from __future__ import absolute_import, division, unicode_literals

import json
import logging

from cStringIO import StringIO
from flask.ext.restful import reqparse
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
    Project, Build, Job, JobPlan, Repository, RepositoryStatus, Patch,
    ProjectOption, ItemOption, Source, PlanStatus, ProjectPlan, Revision
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
        commit = vcs.log(parent=treeish, limit=1).next()
    except Exception:
        # TODO(dcramer): it's possible to DOS the endpoint by passing invalid
        # commits so we should really cache the failed lookups
        raise MissingRevision('Unable to find revision %s' % (treeish,))

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

    filters = []
    if green_rev:
        if green_rev.status == Status.finished and green_rev.result == Result.passed:
            return sha
        filters.append(Build.date_created > green_rev.date_created)

    latest_green = Build.query.join(
        Source, Source.id == Build.source_id,
    ).filter(
        Build.status == Status.finished,
        Build.result == Result.passed,
        Build.project_id == project.id,
        Source.patch_id == None,  # NOQA
        Source.revision_sha != None,
        Source.repository_id == project.repository_id,
        *filters
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
        if patch:
            source, _ = get_or_create(Source, where={
                'patch': patch,
            }, defaults={
                'repository': repository,
                'revision_sha': sha,
                'data': source_data or {},
            })

        else:
            source, _ = get_or_create(Source, where={
                'repository': repository,
                'patch': None,
                'revision_sha': sha,
            }, defaults={
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


def get_build_plans(project):
    return [p for p in project.plans if p.status == PlanStatus.active]


def execute_build(build):
    # TODO(dcramer): most of this should be abstracted into sync_build as if it
    # were a "im on step 0, create step 1"
    project = build.project

    jobs = []
    for plan in get_build_plans(project):
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

        jobplan = JobPlan.build_jobplan(plan, job)

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
        build_id=build.id.hex,
        task_id=build.id.hex,
    )

    return build


def get_repository_by_callsign(callsign):
    # It's possible to have multiple repositories with the same callsign due
    # to us not enforcing a unique constraint (via options). Given that it is
    # complex and shouldn't actually happen we make an assumption that there's
    # only a single repo
    item_id_list = db.session.query(ItemOption.item_id).filter(
        ItemOption.name == 'phabricator.callsign',
        ItemOption.value == callsign,
    )
    repo_list = list(Repository.query.filter(
        Repository.id.in_(item_id_list),
        Repository.status == RepositoryStatus.active,
    ))
    if len(repo_list) > 1:
        logging.warning('Multiple repositories found matching phabricator.callsign=%s', callsign)
    elif len(repo_list) < 1:
        return None  # Match behavior of project and repository parameters
    return repo_list[0]


def get_repository_by_url(url):
    return Repository.query.filter(
        Repository.url == url,
        Repository.status == RepositoryStatus.active,
    ).first()


class BuildIndexAPIView(APIView):
    parser = reqparse.RequestParser()
    parser.add_argument('sha', type=str, required=True)
    parser.add_argument('project', type=lambda x: Project.query.filter(
        Project.slug == x,
        Project.status == ProjectStatus.active,
    ).first())
    # TODO(dcramer): it might make sense to move the repository and callsign
    # options into something like a "repository builds index" endpoint
    parser.add_argument('repository', type=get_repository_by_url)
    parser.add_argument('repository[phabricator.callsign]', type=get_repository_by_callsign)
    parser.add_argument('author', type=AuthorValidator())
    parser.add_argument('label', type=unicode)
    parser.add_argument('target', type=unicode)
    parser.add_argument('message', type=unicode)
    parser.add_argument('patch', type=FileStorage, dest='patch_file', location='files')
    parser.add_argument('patch[data]', type=unicode, dest='patch_data')

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

        if not (args.project or args.repository or args['repository[phabricator.callsign]']):
            return {"error": "Project or repository must be specified"}, 400

        if args.patch_data:
            try:
                patch_data = json.loads(args.patch_data)
            except Exception:
                return {"error": "Invalid patch data (must be JSON dict)"}, 400

            if not isinstance(patch_data, dict):
                return {"error": "Invalid patch data (must be JSON dict)"}, 400
        else:
            patch_data = None

        if args.project:
            projects = [args.project]
            repository = Repository.query.get(args.project.repository_id)

        elif args.repository:
            repository = args.repository
            projects = list(Project.query.options(
                subqueryload_all(Project.project_plans, ProjectPlan.plan),
            ).filter(
                Project.status == ProjectStatus.active,
                Project.repository_id == repository.id,
            ))

        elif args['repository[phabricator.callsign]']:
            repository = args['repository[phabricator.callsign]']
            projects = list(Project.query.options(
                subqueryload_all(Project.project_plans, ProjectPlan.plan),
            ).filter(
                Project.status == ProjectStatus.active,
                Project.repository_id == repository.id,
            ))

        if not projects:
            return {"error": "Unable to find project(s)."}, 400

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
            return {"error": "Unable to find commit %s in %s." % (
                args.sha, repository.url)}, 400

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
            fp = StringIO()
            for line in args.patch_file:
                fp.write(line)
            patch_file = fp
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
            plan_list = get_build_plans(project)
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

            forced_sha = sha
            # TODO(dcramer): find_green_parent_sha needs to take branch
            # into account
            # if patch_file:
            #     forced_sha = find_green_parent_sha(
            #         project=project,
            #         sha=sha,
            #     )

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
