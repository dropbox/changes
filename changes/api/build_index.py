from __future__ import absolute_import, division, unicode_literals

import json
import logging
import uuid

from cStringIO import StringIO
from flask.ext.restful import reqparse
from sqlalchemy.orm import joinedload, subqueryload_all
from werkzeug.datastructures import FileStorage

from changes.api.base import APIView, error
from changes.api.validators.author import AuthorValidator
from changes.config import db, statsreporter
from changes.constants import Result, Status, ProjectStatus
from changes.db.utils import get_or_create
from changes.jobs.create_job import create_job
from changes.jobs.sync_build import sync_build
from changes.models import (
    Project, ProjectOptionsHelper, Build, Job, JobPlan, Repository,
    RepositoryStatus, Patch, ItemOption, Source, PlanStatus, Revision
)
from changes.utils.diff_parser import DiffParser
from changes.utils.whitelist import in_project_files_whitelist
from changes.vcs.base import CommandError, UnknownRevision


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
    except CommandError:
        # update and try one more time
        vcs.update()
        try:
            commit = vcs.log(parent=treeish, limit=1).next()
        except CommandError:
            # TODO(dcramer): it's possible to DOS the endpoint by passing invalid
            # commits so we should really cache the failed lookups
            raise MissingRevision('Unable to find revision %s' % (treeish,))

    revision, _, __ = commit.save(repository)

    return revision


def _get_revision_changed_files(repository, revision):
    vcs = repository.get_vcs()
    if not vcs:
        raise NotImplementedError

    try:
        diff = vcs.export(revision.sha)
    except UnknownRevision:
        vcs.update()
        try:
            diff = vcs.export(revision.sha)
        except UnknownRevision:
            raise MissingRevision('Unable to find revision %s' % (revision.sha,))

    diff_parser = DiffParser(diff)
    return diff_parser.get_changed_files()


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


def create_build(project, collection_id, label, target, message, author,
                 change=None, patch=None, cause=None, source=None, sha=None,
                 source_data=None, tag=None):
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

    statsreporter.stats().incr('new_api_build')

    build = Build(
        project=project,
        project_id=project.id,
        collection_id=collection_id,
        source=source,
        source_id=source.id if source else None,
        status=Status.queued,
        author=author,
        author_id=author.id if author else None,
        label=label,
        target=target,
        message=message,
        cause=cause,
        tags=[tag] if tag else [],
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
    elif not repo_list:
        return None  # Match behavior of project and repository parameters
    return repo_list[0]


def get_repository_by_url(url):
    return Repository.query.filter(
        Repository.url == url,
        Repository.status == RepositoryStatus.active,
    ).first()


def try_get_projects_and_repository(args):
    """Given a set of HTTP POST arguments, try and find the appropriate
    projects and repository.

    Possible inputs:
        project
        Returns: (A list containing only this project) * its repository

        repository
        Returns: All active projects for this repo * repo

        repository living at key 'repository[phabricator.callsign]'
        Returns: All active projects for this repo * repo
    """
    if args.project:
        repository = Repository.query.get(args.project.repository_id)
        return [args.project], repository
    elif args.repository:
        repository = args.repository
        projects = list(Project.query.options(
            subqueryload_all('plans'),
        ).filter(
            Project.status == ProjectStatus.active,
            Project.repository_id == repository.id,
        ))
        return projects, repository
    elif args['repository[phabricator.callsign]']:
        repository = args['repository[phabricator.callsign]']
        projects = list(Project.query.options(
            subqueryload_all('plans'),
        ).filter(
            Project.status == ProjectStatus.active,
            Project.repository_id == repository.id,
        ))
        return projects, repository
    else:
        return None, None


class BuildIndexAPIView(APIView):
    parser = reqparse.RequestParser()

    """The commit ID to base this build on. A patch may also be applied - see below.
    """
    parser.add_argument('sha', type=str, required=True)

    """The project slug to build.
    Optional
    """
    parser.add_argument('project', type=lambda x: Project.query.filter(
        Project.slug == x,
        Project.status == ProjectStatus.active,
    ).first())

    # TODO(dcramer): it might make sense to move the repository and callsign
    # options into something like a "repository builds index" endpoint
    """The repository url for the repo to build with.
    Optional
    """
    parser.add_argument('repository', type=get_repository_by_url)

    """The Phabricator callsign for the repo to build with.
    Optional
    """
    parser.add_argument('repository[phabricator.callsign]', type=get_repository_by_callsign)

    """Optional author for this build. If nothing is passed in, the commit
    author is used. See AuthorValidator for format.
    """
    parser.add_argument('author', type=AuthorValidator())

    """Optional label to store with this build. If nothing is passed in,
    the commit subject for the revision is used.
    """
    parser.add_argument('label', type=unicode)

    """Optional indicator of what is being built, like a Phabricator revision
    D1234. If nothing is passed in, parts of the sha is used.
    """
    parser.add_argument('target', type=unicode)

    """Optional message to tag along with the created builds. If nothing is passed
    in, the commit message of the revision is used.
    """
    parser.add_argument('message', type=unicode)

    """The optional patch to apply to the given revision before building. This must
    be the same format as a `git diff` for a git repo. This is attached as a file.

    Use this to create a diff build. Omit to create a commit build.
    """
    parser.add_argument('patch', type=FileStorage, dest='patch_file', location='files')

    """Additional metadata to attach to the patch. This must be in serialized
    JSON format, and will be stored in the Source model as the data column.

    If nothing is passed in, then an empty dictionary is saved in the data column
    """
    parser.add_argument('patch[data]', type=unicode, dest='patch_data')

    """A tag that will get stored with created build. Can be used to track
    the cause of this build (i.e. commit-queue)
    """
    parser.add_argument('tag', type=unicode)

    """A JSON list of project slugs that will act as a whitelist, meaning
    only projects with these slugs will be created.
    Optional - if nothing is given, no whitelisting is applied
    """
    parser.add_argument('project_whitelist', type=lambda x: json.loads(x))

    """A flag to indicate whether the file whitelist should be used to filter
    out projects. Defaults to true for diff builds and false for commit builds
    for compatibility reasons
    """
    parser.add_argument('apply_file_whitelist', type=bool)

    """A flag to indicate that for each project, if there is an existing build,
    return the latest build. Only when there are no builds for a project is
    one created. This is done at the very end, after all the filters.

    Optional - defaults to False
    """
    parser.add_argument('ensure_only', type=bool, default=False)

    def get(self):
        queryset = Build.query.options(
            joinedload('project'),
            joinedload('author'),
            joinedload('source').joinedload('revision'),
        ).order_by(Build.date_created.desc(), Build.date_started.desc())

        return self.paginate(queryset)

    def post(self):
        """
        Create a new commit or diff build. The API roughly goes like this:

        1. Identify the project(s) to build for. This can be done by specifying
        ``project``, ``repository``, or ``repository[callsign]``. If a repository is
        specified somehow, then all projects for that repository are considered
        for building.

        2. Using the ``sha``, find the appropriate revision object. This may
        involve updating the repo.

        3. If ``patch`` is given, then apply the patch and mark this as a diff build.
        Otherwise, this is a commit build.

        4. If provided, apply project_whitelist, filtering out projects not in
        this whitelist.

        5. Based on the flag ``apply_file_whitelist`` (see comment on the argument
        itself for default values), decide whether or not to filter out projects
        by file whitelist.

        6. Attach metadata and create/ensure existence of a build for each project,
        depending on the flag ``ensure_only``.

        NOTE: In ensure-only mode, the collection_ids of the returned builds are
        not necessarily identical, as we give new builds new collection IDs
        and preserve the existing builds' collection IDs.

        NOTE: If ``patch`` is specified ``sha`` is assumed to be the original
        base revision to apply the patch.

        Not relevant until we fix TODO: ``sha`` is **not** guaranteed to be the rev
        used to apply the patch. See ``find_green_parent_sha`` for the logic of
        identifying the correct revision.
        """
        args = self.parser.parse_args()

        if not (args.project or args.repository or args['repository[phabricator.callsign]']):
            return error("Project or repository must be specified",
                         problems=["project", "repository",
                                   "repository[phabricator.callsign]"])

        # read arguments
        if args.patch_data:
            try:
                patch_data = json.loads(args.patch_data)
            except Exception:
                return error("Invalid patch data (must be JSON dict)",
                             problems=["patch[data]"])

            if not isinstance(patch_data, dict):
                return error("Invalid patch data (must be JSON dict)",
                             problems=["patch[data]"])
        else:
            patch_data = None

        # 1. identify project(s)
        projects, repository = try_get_projects_and_repository(args)

        if not projects:
            return error("Unable to find project(s).")

        # read arguments
        label = args.label
        author = args.author
        message = args.message
        tag = args.tag

        if not tag and args.patch_file:
            tag = 'patch'

        # 2. find revision
        try:
            revision = identify_revision(repository, args.sha)
        except MissingRevision:
            # if the default fails, we absolutely can't continue and the
            # client should send a valid revision
            return error("Unable to find commit %s in %s." % (
                args.sha, repository.url), problems=['sha', 'repository'])

        # get default values for arguments
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

        # 3. Check for patch
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

        project_options = ProjectOptionsHelper.get_options(projects, ['build.file-whitelist'])

        # mark as commit or diff build
        if not patch:
            is_commit_build = True
        else:
            is_commit_build = False

        if args.apply_file_whitelist is not None:
            apply_file_whitelist = args.apply_file_whitelist
        elif is_commit_build:
            apply_file_whitelist = False
        else:
            apply_file_whitelist = True

        if apply_file_whitelist:
            if patch:
                diff_parser = DiffParser(patch.diff)
                files_changed = diff_parser.get_changed_files()
            elif revision:
                try:
                    files_changed = _get_revision_changed_files(repository, revision)
                except MissingRevision:
                    return error("Unable to find commit %s in %s." % (
                        args.sha, repository.url), problems=['sha', 'repository'])
            else:
                # the only way that revision can be null is if this repo does not have a vcs backend
                logging.warning('Revision and patch are both None for sha %s. This is because the repo %s does not have a VCS backend.', sha, repository.url)
                files_changed = None
        else:
            # we won't be applying file whitelist, so there is no need to get the list of changed files.
            files_changed = None

        collection_id = uuid.uuid4()
        builds = []
        for project in projects:
            plan_list = get_build_plans(project)
            if not plan_list:
                logging.warning('No plans defined for project %s', project.slug)
                continue
            # 4. apply project whitelist as appropriate
            if args.project_whitelist is not None and project.slug not in args.project_whitelist:
                logging.info('Project %s is not in the supplied whitelist', project.slug)
                continue
            forced_sha = sha
            # TODO(dcramer): find_green_parent_sha needs to take branch
            # into account
            # if patch_file:
            #     forced_sha = find_green_parent_sha(
            #         project=project,
            #         sha=sha,
            #     )

            # 5. apply file whitelist as appropriate
            if apply_file_whitelist and files_changed and not in_project_files_whitelist(project_options[project.id], files_changed):
                logging.info('No changed files matched build.file-whitelist for project %s', project.slug)
                continue

            # 6. create/ensure build
            if args.ensure_only:
                potentials = list(Build.query.filter(
                    Build.project_id == project.id,
                    Build.source.has(revision_sha=sha),
                ).order_by(
                    Build.date_created.desc()  # newest first
                ).limit(1))
                if len(potentials) == 0:
                    builds.append(create_build(
                        project=project,
                        collection_id=collection_id,
                        sha=forced_sha,
                        target=target,
                        label=label,
                        message=message,
                        author=author,
                        patch=patch,
                        source_data=patch_data,
                        tag=tag,
                    ))
                else:
                    builds.append(potentials[0])
            else:
                builds.append(create_build(
                    project=project,
                    collection_id=collection_id,
                    sha=forced_sha,
                    target=target,
                    label=label,
                    message=message,
                    author=author,
                    patch=patch,
                    source_data=patch_data,
                    tag=tag,
                ))

        return self.respond(builds)
