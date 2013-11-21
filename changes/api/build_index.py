from __future__ import absolute_import, division, unicode_literals

from cStringIO import StringIO
from datetime import datetime
from flask import request
from sqlalchemy.orm import joinedload

from changes.api.base import APIView, param
from changes.api.validators.author import AuthorValidator
from changes.config import db, queue
from changes.constants import Status, NUM_PREVIOUS_RUNS
from changes.models import Project, Build, Repository, Patch, Change


class BuildIndexAPIView(APIView):
    @param('change_id', lambda x: Change.query.get(x), dest='change', required=False)
    def get(self, change=None):
        queryset = Build.query.options(
            joinedload(Build.project),
            joinedload(Build.author),
        ).order_by(Build.date_created.desc(), Build.date_started.desc())
        if change:
            queryset = queryset.filter_by(change=change)

        build_list = list(queryset)[:NUM_PREVIOUS_RUNS]

        context = {
            'builds': build_list,
        }

        return self.respond(context)

    # TODO(dcramer): these params are getting messy, and in this case we've got
    # multiple input styles (GET vs POST) that can potentially squash each other
    @param('change', lambda x: Change.query.get(x), dest='change', required=False)
    @param('change_id', lambda x: Change.query.get(x), dest='change', required=False)
    @param('project', lambda x: Project.query.filter_by(slug=x).first(), dest='project', required=False)
    @param('repository', lambda x: Repository.query.filter_by(url=x).first(), dest='repository', required=False)
    @param('sha', required=False)
    @param('author', AuthorValidator(), required=False)
    @param('label', required=False)
    @param('target', required=False)
    @param('message', required=False)
    @param('patch[label]', required=False, dest='patch_label')
    def post(self, project=None, sha=None, change=None, author=None,
             patch_label=None, patch=None, label=None, target=None,
             message=None, repository=None):

        assert change or project or repository

        if request.form.get('patch'):
            raise ValueError('patch')

        patch_file = request.files.get('patch')

        if patch_file and not patch_label:
            raise ValueError('patch_label')

        if change:
            projects = [change.project]
            repository = Repository.query.get(change.project.repository_id)
        elif project:
            projects = [project]
            repository = Repository.query.get(project.repository_id)
        else:
            projects = list(Project.query.filter(
                Project.repository_id == repository.id,
            ))

        if not label:
            label = "A homeless build"
        else:
            label = label[:128]

        if not target:
            if patch_label:
                target = patch_label
            elif sha:
                target = sha[:12]
        else:
            target = target[:128]

        if patch_file:
            fp = StringIO()
            for line in patch_file:
                fp.write(line)

        builds = []
        for project in projects:
            if patch_file:
                patch = Patch(
                    change=change,
                    repository=repository,
                    project=project,
                    parent_revision_sha=sha,
                    label=patch_label,
                    diff=fp.getvalue(),
                )
                db.session.add(patch)
            else:
                patch = None

            build = Build(
                change=change,
                project=project,
                repository=repository,
                status=Status.queued,
                author=author,
                label=label,
                target=target,
                revision_sha=sha,
                message=message,
            )

            if change:
                build.change = change
                change.date_modified = datetime.utcnow()
                db.session.add(change)

            if patch:
                build.patch = patch

            db.session.add(build)
            db.session.commit()

            queue.delay('create_build', kwargs={
                'build_id': build.id.hex,
            }, countdown=5)

            builds.append(build)

        context = {
            'builds': [
                {
                    'id': b.id.hex,
                    'project': b.project,
                    'link': '/builds/{0}/'.format(b.id.hex),
                } for b in builds
            ],
        }

        return self.respond(context)

    def get_stream_channels(self, change_id=None):
        if not change_id:
            return ['builds:*']
        return ['builds:{0}:*'.format(change_id)]
