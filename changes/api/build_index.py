from __future__ import absolute_import, division, unicode_literals

import json
import logging

from flask.ext.restful import reqparse
from io import StringIO
from sqlalchemy.orm import joinedload, subqueryload_all
from werkzeug.datastructures import FileStorage

from changes.api.base import APIView
from changes.api.validators.author import AuthorValidator
from changes.config import db
from changes.constants import Result, Status, ProjectStatus
from changes.db.utils import get_or_create
from changes.jobs.create_job import create_job
from changes.jobs.sync_build import sync_build
from changes.models import (
    Project, Build, Job, JobPlan, Repository, Patch, ProjectOption,
    ItemOption, Source, ProjectPlan, Revision
)


class MissingRevision(Exception):
    pass


def identify_revision(repository, treeish):
    """
    Attempt to transform a a commit-like reference into a valid revision.
    """
    # try to find it from the database first
    if len(treeish) == 40:
        revision = Revision.query.filter(
            Revision.repository_id == repository.id,
            Revision.sha == treeish,
        ).first()
        if revision:
            return revision

    vcs = repository.get_vcs()
    if not vcs:
        return

    try:
        commit = next(vcs.log(parent=treeish, limit=1))
    except Exception:
        # fall back to HEAD/tip when a matching revision isn't found
        # this case happens frequently with gateways like hg-git
        # TODO(dcramer): it's possible to DOS the endpoint by passing invalid
        # commits so we should really cache the failed lookups
        tree = vcs.get_default_revision()
        try:
            commit = next(vcs.log(parent=tree, limit=1))
        except Exception:
            raise MissingRevision('Unable to find revision %s' % (tree,))

    revision, _ = commit.save(repository)

    return revision


def find_green_parent_sha(project, sha):
    """
    Attempt to find a better revision than ``sha`` that is green.

    - If sha is green, let it ride.
    - Only search future revisions.
    - Find the newest revision (more likely to conflict).
    - If there's nothing better, return existing sha.
    """
    green_rev = Build.query.join(
        Source, Source.id == Build.source_id,
    ).filter(
        Source.repository_id == project.repository_id,
        Source.revision_sha == sha,
    ).first()
    if green_rev:
        if green_rev.status == Status.finished and green_rev.result == Result.passed:
            return sha

        latest_green = Build.query.filter(
            Build.date_created > green_rev.date_created,
            Build.status == Status.finished,
            Build.result == Result.passed,
        ).order_by(Build.date_created.desc()).first()
    else:
        latest_green = Build.query.filter(
            Build.status == Status.finished,
            Build.result == Result.passed,
        ).order_by(Build.date_created.desc()).first()

    if latest_green:
        return latest_green.source.revision_sha

    return sha


def create_build(project, label, target, message, author, change=None,
                 patch=None, cause=None, source=None, sha=None,
                 source_data=None):
    assert sha or source

    repository = project.repository

    if source is None:
        source, _ = get_or_create(Source, where={
            'repository': repository,
            'patch': patch,
            'revision_sha': sha,
            'data': source_data or {},
        })

    build = Build(
        project=project,
        project_id=project.id,
        source=source,
        source_id=source.id if source else None,
        status=Status.queued,
        author=author,
        author_id=author.id if author else None,
        label=label,
        target=target,
        message=message,
        cause=cause,
    )

    db.session.add(build)
    db.session.commit()

    execute_build(build=build)

    return build


def execute_build(build):
    # TODO(dcramer): most of this should be abstracted into sync_build as if it
    # were a "im on step 0, create step 1"
    project = build.project

    jobs = []
    for plan in project.plans:
        job = Job(
            build=build,
            build_id=build.id,
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

    db.session.commit()

    for job in jobs:
        create_job.delay(
            job_id=job.id.hex,
            task_id=job.id.hex,
            parent_task_id=job.build_id.hex,
        )

    db.session.commit()

    sync_build.delay(
        build_id=job.build_id.hex,
        task_id=job.build_id.hex,
    )

    return build


class BuildIndexAPIView(APIView):
    parser = reqparse.RequestParser()
    parser.add_argument('sha', required=True)
    parser.add_argument('project', type=lambda x: Project.query.filter(
        Project.slug == x,
        Project.status == ProjectStatus.active,
    ).first())
    parser.add_argument('repository', type=lambda x: Repository.query.filter_by(url=x).first())
    parser.add_argument('author', type=AuthorValidator())
    parser.add_argument('label')
    parser.add_argument('target')
    parser.add_argument('message')
    parser.add_argument('patch', type=FileStorage, dest='patch_file', location='files')
    parser.add_argument('patch[data]', dest='patch_data')

    def get(self):
        queryset = Build.query.options(
            joinedload('project'),
            joinedload('author'),
            joinedload('source').joinedload('revision'),
        ).order_by(Build.date_created.desc(), Build.date_started.desc())

        return self.paginate(queryset)

    def post(self):
        """
        Note: If ``patch`` is specified ``sha`` is assumed to be the original
        base revision to apply the patch. It is **not** guaranteed to be the rev
        used to apply the patch. See ``find_green_parent_sha`` for the logic of
        identifying the correct revision.
        """
        args = self.parser.parse_args()

        if not (args.project or args.repository):
            return '{"error": "Need project or repository"}', 400

        if args.patch_data:
            try:
                patch_data = json.loads(args.patch_data)
            except Exception:
                return '{"error": "Invalid patch data (must be JSON dict)"}', 400

            if not isinstance(patch_data, dict):
                return '{"error": "Invalid patch data (must be JSON dict)"}', 400
        else:
            patch_data = None

        if args.project:
            projects = [args.project]
            repository = Repository.query.get(args.project.repository_id)
        else:
            repository = args.repository
            projects = list(Project.query.options(
                subqueryload_all(Project.project_plans, ProjectPlan.plan),
            ).filter(
                Project.status == ProjectStatus.active,
                Project.repository_id == repository.id,
            ))

        if not projects:
            return '{"error": "Unable to find project(s)."}', 400

        if args.patch_file:
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
                return self.respond([])

        label = args.label
        author = args.author
        message = args.message

        try:
            revision = identify_revision(repository, args.sha)
        except MissingRevision:
            # if the default fails, we absolutely can't continue and the
            # client should send a valid revision
            return '{"error": "Unable to find a commit to build."}', 400

        if revision:
            if not author:
                author = revision.author
            if not label:
                label = revision.subject
            # only default the message if its absolutely not set
            if message is None:
                message = revision.message
            sha = revision.sha
        else:
            sha = args.sha

        if not args.target:
            target = sha[:12]
        else:
            target = args.target[:128]

        if not label:
            if message:
                label = message.splitlines()[0]
            if not label:
                label = 'A homeless build'
        label = label[:128]

        if args.patch_file:
            patch_file = StringIO()
            patch_file.write(args.patch_file.read().decode('utf-8'))
        else:
            patch_file = None

        if patch_file:
            patch = Patch(
                repository=repository,
                parent_revision_sha=sha,
                diff=patch_file.getvalue(),
            )
            db.session.add(patch)
        else:
            patch = None

        builds = []
        for project in projects:
            plan_list = list(project.plans)
            if not plan_list:
                logging.warning('No plans defined for project %s', project.slug)
                continue

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
                forced_sha = find_green_parent_sha(
                    project=project,
                    sha=sha,
                )
            else:
                forced_sha = sha

            builds.append(create_build(
                project=project,
                sha=forced_sha,
                target=target,
                label=label,
                message=message,
                author=author,
                patch=patch,
                source_data=patch_data,
            ))

        return self.respond(builds)

    def get_stream_channels(self):
        return ['builds:*']
