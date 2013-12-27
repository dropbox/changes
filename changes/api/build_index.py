from __future__ import absolute_import, division, unicode_literals

import warnings

from cStringIO import StringIO
from datetime import datetime
from flask import request
from sqlalchemy.orm import joinedload
from sqlalchemy.sql import func

from changes.api.base import APIView, param
from changes.api.validators.author import AuthorValidator
from changes.config import db, queue
from changes.constants import Status, NUM_PREVIOUS_RUNS
from changes.db.funcs import coalesce
from changes.db.utils import get_or_create
from changes.models import (
    Project, Build, Job, JobPlan, Repository, Patch, ProjectOption,
    Change, ItemOption, Source
)
from changes.utils.http import build_uri


def create_build(project, sha, label, target, message, author, change=None,
                 patch_file=None, patch_label=None):
    repository = project.repository

    plan_list = list(project.plans)
    if plan_list and patch_file:
        options = dict(
            db.session.query(
                ItemOption.item_id, ItemOption.value
            ).filter(
                ItemOption.item_id.in_([p.id for p in plan_list]),
                ItemOption.name.in_([
                    'build.allow-patches',
                ])
            )
        )
        plan_list = [
            p for p in plan_list
            if options.get(p.id, '1') == '1'
        ]

        # no plans remained
        if not plan_list:
            return []

    if patch_file:
        patch = Patch(
            change=change,
            repository=repository,
            project=project,
            parent_revision_sha=sha,
            label=patch_label,
            diff=patch_file.getvalue(),
        )
        db.session.add(patch)
    else:
        patch = None

    if sha or patch:
        source, _ = get_or_create(Source, where={
            'repository': repository,
            'patch': patch,
            'revision_sha': sha,
        })
    else:
        source = None

    jobs = []

    # TODO(dcramer): find a way to abstract this
    cur_no_query = db.session.query(
        coalesce(func.max(Build.number), 0)
    ).filter(
        Build.project_id == project.id,
    ).scalar()

    build = Build(
        number=cur_no_query + 1,
        project=project,
        source=source,
        repository=repository,
        status=Status.queued,
        author=author,
        label=label,
        target=target,
        revision_sha=sha,
        patch=patch,
        message=message,
    )

    db.session.add(build)

    if not plan_list:
        # Legacy support
        # TODO(dcramer): remove this after we transition to plans
        warnings.warn('{0} is missing a build plan. Falling back to legacy mode.')

        cur_no_query = db.session.query(
            coalesce(func.max(Job.number), 0)
        ).filter(
            Job.build_id == build.id,
        ).scalar()

        job = Job(
            build=build,
            number=cur_no_query + 1,
            source=source,
            project=project,
            repository=repository,
            status=Status.queued,
            author=author,
            label=label,
            target=target,
            revision_sha=sha,
            message=message,
            patch=patch,
            change=change,
        )

        db.session.add(job)

        jobs.append(job)

    for plan in plan_list:
        cur_no_query = db.session.query(
            coalesce(func.max(Job.number), 0)
        ).filter(
            Job.build_id == build.id,
        ).scalar()

        job = Job(
            build=build,
            number=cur_no_query + 1,
            project=project,
            source=source,
            repository=repository,
            status=Status.queued,
            author=author,
            label=plan.label,
            target=target,
            revision_sha=sha,
            patch=patch,
            change=change,
        )

        db.session.add(job)

        jobplan = JobPlan(
            project=project,
            job=job,
            build=build,
            plan=plan,
        )

        db.session.add(jobplan)

        jobs.append(job)

    if change:
        change.date_modified = datetime.utcnow()
        db.session.add(change)

    db.session.commit()

    for job in jobs:
        queue.delay('create_job', kwargs={
            'job_id': job.id.hex,
        }, countdown=5)

    return build


class BuildIndexAPIView(APIView):
    @param('change_id', lambda x: Change.query.get(x), dest='change', required=False)
    def get(self, change=None):
        queryset = Job.query.options(
            joinedload(Job.project),
            joinedload(Job.author),
        ).order_by(Job.date_created.desc(), Job.date_started.desc())
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

        if patch_file:
            # eliminate projects without diff builds
            options = dict(
                db.session.query(
                    ProjectOption.project_id, ProjectOption.value
                ).filter(
                    ProjectOption.project_id.in_([p.id for p in projects]),
                    ProjectOption.name.in_([
                        'build.allow-patches',
                    ])
                )
            )

            projects = [
                p for p in projects
                if options.get(p.id, '1') == '1'
            ]

        if not projects:
            return self.respond({'builds': []})

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
            patch_file = fp

        builds = []
        for project in projects:
            builds.append(create_build(
                project=project,
                change=change,
                sha=sha,
                target=target,
                label=label,
                message=message,
                author=author,
                patch_label=patch_label,
                patch_file=patch_file,
            ))

        context = {
            'builds': [
                {
                    'id': b.id.hex,
                    'project': b.project,
                    'link': build_uri('/builds/{0}/'.format(b.id.hex)),
                } for b in builds
            ],
        }

        return self.respond(context)

    def get_stream_channels(self, change_id=None):
        if not change_id:
            return ['jobs:*']
        return ['jobs:{0}:*'.format(change_id)]
