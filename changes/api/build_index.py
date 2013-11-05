from __future__ import absolute_import, division, unicode_literals

from cStringIO import StringIO
from datetime import datetime
from flask import request
from sqlalchemy.orm import joinedload

from changes.api.base import APIView, param
from changes.api.validators.author import AuthorValidator
from changes.config import db, queue
from changes.constants import Status
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

        build_list = list(queryset)[:25]

        context = {
            'builds': build_list,
        }

        return self.respond(context)

    @param('sha')
    # TODO(dcramer): these params are getting messy, and in this case we've got
    # multiple input styles (GET vs POST) that can potentially squash each other
    @param('change', lambda x: Change.query.get(x), dest='change', required=False)
    @param('change_id', lambda x: Change.query.get(x), dest='change', required=False)
    @param('project', lambda x: Project.query.filter_by(slug=x).first(), dest='project', required=False)
    @param('author', AuthorValidator(), required=False)
    @param('label', required=False)
    @param('message', required=False)
    @param('patch[label]', required=False, dest='patch_label')
    @param('patch[url]', required=False, dest='patch_url')
    def post(self, sha, project=None, change=None, author=None,
             patch_label=None, patch_url=None, patch=None, label=None,
             message=None):

        assert change or project

        if request.form.get('patch'):
            raise ValueError('patch')

        patch_file = request.files.get('patch')
        patch_label = request.form.get('patch_label')
        patch_url = request.form.get('patch_url')

        if patch_file and not patch_label:
            raise ValueError('patch_label')

        if change:
            project = change.project
        repository = Repository.query.get(project.repository_id)

        if patch_file:
            fp = StringIO()
            for line in patch_file:
                fp.write(line)

            patch = Patch(
                change=change,
                repository=repository,
                project=project,
                parent_revision_sha=sha,
                label=patch_label,
                url=patch_url,
                diff=fp.getvalue(),
            )
            db.session.add(patch)
        else:
            patch = None

        if not label:
            if patch_label:
                label = patch_label
            else:
                label = sha[:12]

        build = Build(
            project=project,
            repository=repository,
            status=Status.queued,
            author=author,
            label=label,
            parent_revision_sha=sha,
            message=message,
        )

        if change:
            build.change = change
            change.date_modified = datetime.utcnow()
            db.session.add(change)

        if patch:
            build.patch = patch

        db.session.add(build)

        queue.delay('create_build', kwargs={
            'build_id': build.id.hex,
        })

        context = {
            'build': {
                'id': build.id.hex,
                'link': '/builds/{0}/'.format(build.id.hex),
            },
        }

        return self.respond(context)

    def get_stream_channels(self, change_id=None):
        if not change_id:
            return ['builds:*']
        return ['builds:{0}:*'.format(change_id)]
