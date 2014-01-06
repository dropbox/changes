from __future__ import absolute_import, division, unicode_literals

from cStringIO import StringIO
from datetime import datetime
from flask import request
from sqlalchemy.orm import joinedload, subqueryload_all
from sqlalchemy.sql import func

from changes.api.base import APIView, param
from changes.api.validators.author import AuthorValidator
from changes.config import db, queue
from changes.constants import Status
from changes.db.funcs import coalesce
from changes.db.utils import get_or_create
from changes.events import publish_build_update, publish_job_update
from changes.models import (
    Project, Build, Job, JobPlan, Repository, Patch, ProjectOption,
    ItemOption, Source, ProjectPlan
)
from changes.utils.http import build_uri


def create_build(project, label, target, message, author, change=None,
                 patch=None, cause=None, source=None, sha=None):
    assert sha or source

    if not project.plans:
        # Legacy support
        # TODO(dcramer): remove this after we transition to plans
        raise ValueError('No plans defined for project {0}'.format(project))

    repository = project.repository

    if source is None:
        source, _ = get_or_create(Source, where={
            'repository': repository,
            'patch': patch,
            'revision_sha': sha,
        })

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
        project_id=project.id,
        source=source,
        source_id=source.id if source else None,
        repository=repository,
        status=Status.queued,
        author=author,
        author_id=author.id if author else None,
        label=label,
        target=target,
        revision_sha=sha,
        patch=patch,
        message=message,
        cause=cause,
    )

    db.session.add(build)

    for plan in project.plans:
        cur_no_query = db.session.query(
            coalesce(func.max(Job.number), 0)
        ).filter(
            Job.build_id == build.id,
        ).scalar()

        job = Job(
            build=build,
            build_id=build.id,
            number=cur_no_query + 1,
            project=project,
            project_id=project.id,
            source=build.source,
            source_id=build.source_id,
            status=build.status,
            label=plan.label,
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

    publish_build_update(build)

    for job in jobs:
        publish_job_update(job)
        queue.delay('create_job', kwargs={
            'job_id': job.id.hex,
        }, countdown=5)

    return build


class BuildIndexAPIView(APIView):
    def get(self):
        queryset = Build.query.options(
            joinedload(Build.project),
            joinedload(Build.author),
        ).order_by(Build.date_created.desc(), Build.date_started.desc())

        return self.paginate(queryset)

    # TODO(dcramer): these params are getting messy, and in this case we've got
    # multiple input styles (GET vs POST) that can potentially squash each other
    @param('sha')
    @param('project', lambda x: Project.query.filter_by(slug=x).first(), dest='project', required=False)
    @param('repository', lambda x: Repository.query.filter_by(url=x).first(), dest='repository', required=False)
    @param('author', AuthorValidator(), required=False)
    @param('label', required=False)
    @param('target', required=False)
    @param('message', required=False)
    @param('patch[label]', required=False, dest='patch_label')
    def post(self, sha=None, project=None, author=None, patch_label=None, patch=None,
             label=None, target=None, message=None, repository=None):

        assert sha
        assert project or repository

        if request.form.get('patch'):
            raise ValueError('patch')

        patch_file = request.files.get('patch')

        if patch_file and not patch_label:
            raise ValueError('patch_label')

        if project:
            projects = [project]
            repository = Repository.query.get(project.repository_id)
        else:
            projects = list(Project.query.options(
                subqueryload_all(Project.project_plans, ProjectPlan.plan),
            ).filter(
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
                    continue

            if patch_file:
                patch = Patch(
                    repository=repository,
                    project=project,
                    parent_revision_sha=sha,
                    label=patch_label,
                    diff=patch_file.getvalue(),
                )
                db.session.add(patch)
            else:
                patch = None

            builds.append(create_build(
                project=project,
                sha=sha,
                target=target,
                label=label,
                message=message,
                author=author,
                patch=patch,
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

    def get_stream_channels(self):
        return ['builds:*']
