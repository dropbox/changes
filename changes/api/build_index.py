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
from changes.constants import Cause, Result, Status, ProjectStatus
from changes.db.utils import get_or_create
from changes.jobs.create_job import create_job
from changes.jobs.sync_build import sync_build
from changes.models.build import Build
from changes.models.job import Job
from changes.models.jobplan import JobPlan
from changes.models.option import ItemOption, ItemOptionsHelper
from changes.models.patch import Patch
from changes.models.plan import PlanStatus
from changes.models.project import Project, ProjectConfigError, ProjectOptionsHelper
from changes.models.repository import Repository, RepositoryStatus
from changes.models.revision import Revision
from changes.models.snapshot import Snapshot, SnapshotImage, SnapshotStatus
from changes.models.source import Source

from changes.utils.diff_parser import DiffParser
from changes.utils.project_trigger import files_changed_should_trigger_project
from changes.vcs.base import (
    CommandError, ConcurrentUpdateError, InvalidDiffError, UnknownRevision
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
    except CommandError:
        # update and try one more time
        try:
            vcs.update()
        except ConcurrentUpdateError:
            # Retry once if it was already updating.
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
        return vcs.get_changed_files(revision.sha)
    except UnknownRevision:
        try:
            vcs.update()
        except ConcurrentUpdateError:
            # Retry once if it was already updating.
            vcs.update()
        try:
            return vcs.get_changed_files(revision.sha)
        except UnknownRevision:
            raise MissingRevision('Unable to find revision %s' % (revision.sha,))


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
                 source_data=None, tag=None, snapshot_id=None, no_snapshot=False):
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

    execute_build(build=build, snapshot_id=snapshot_id, no_snapshot=no_snapshot)

    return build


def get_build_plans(project):
    return [p for p in project.plans if p.status == PlanStatus.active]


def execute_build(build, snapshot_id, no_snapshot):
    if no_snapshot:
        assert snapshot_id is None, 'Cannot specify snapshot with no_snapshot option'
    # TODO(dcramer): most of this should be abstracted into sync_build as if it
    # were a "im on step 0, create step 1"
    project = build.project

    # We choose a snapshot before creating jobplans. This is so that different
    # jobplans won't end up using different snapshots in a build.
    if snapshot_id is None and not no_snapshot:
        snapshot = Snapshot.get_current(project.id)
        if snapshot:
            snapshot_id = snapshot.id

    plans = get_build_plans(project)

    options = ItemOptionsHelper.get_options([p.id for p in plans], ['snapshot.require'])

    jobs = []
    for plan in get_build_plans(project):
        if (options[plan.id].get('snapshot.require', '0') == '1' and
                not no_snapshot and
                SnapshotImage.get(plan, snapshot_id) is None):
            logging.warning('Skipping plan %r (%r) because no snapshot exists yet', plan.label, project.slug)
            continue

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

        jobplan = JobPlan.build_jobplan(plan, job, snapshot_id=snapshot_id)

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

    """Deprecated. This means the same thing as `apply_project_files_trigger`,
    and if both are present, `apply_project_files_trigger` is used.
    """
    parser.add_argument('apply_file_whitelist', type=bool)

    """A flag to indicate whether the file blacklist and whitelist should be
    used to filter out projects. Defaults to true for diff builds and false for
    commit builds for compatibility reasons.
    """
    parser.add_argument('apply_project_files_trigger', type=bool)

    """A flag to indicate that for each project, if there is an existing build,
    return the latest build. Only when there are no builds for a project is
    one created. This is done at the very end, after all the filters.

    TODO: right now this only works with a commit build. The issue is that
    for diff build, we are always creating a new Patch object. We can
    change that behavior to instead retrieve an existing Patch object, but
    that would be a potentially significant behavior change and should only
    be done when we actually have a use case for ensure-only mode in a diff
    build.

    Optional - defaults to False
    """
    parser.add_argument('ensure_only', type=bool, default=False)

    """Optional id of the snapshot to use for this build. If none is given,
    the current active snapshot for the project(s) will be used. To use no snapshot,
    use the `no_snapshot` flag described below.
    """
    parser.add_argument('snapshot_id', type=uuid.UUID, default=None)

    """Optional flag to force the build to use no snapshot."""
    parser.add_argument('no_snapshot', type=bool, default=False)

    """Cause for the build (based on the Cause enum). Limited to avoid confusion."""
    parser.add_argument('cause', type=unicode, choices=('unknown', 'manual'), default='unknown')

    get_parser = reqparse.RequestParser()

    """Optional tag to search for."""
    get_parser.add_argument('tag', type=str, default='')

    def get(self):
        queryset = Build.query.options(
            joinedload('project'),
            joinedload('author'),
            joinedload('source').joinedload('revision'),
        ).order_by(Build.date_created.desc(), Build.date_started.desc())

        args = self.get_parser.parse_args()
        if args.tag:
            queryset = queryset.filter(Build.tags.any(args.tag))

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

        4. If ``snapshot_id`` is given, verify that the snapshot can be used by all
        projects.

        5. If provided, apply project_whitelist, filtering out projects not in
        this whitelist.

        6. Based on the flag ``apply_project_files_trigger`` (see comment on the argument
        itself for default values), decide whether or not to filter out projects
        by file blacklist and whitelist.

        7. Attach metadata and create/ensure existence of a build for each project,
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

        if args.patch_file and args.ensure_only:
            return error("Ensure-only mode does not work with a diff build yet.",
                         problems=["patch", "ensure_only"])

        if not (args.project or args.repository or args['repository[phabricator.callsign]']):
            return error("Project or repository must be specified",
                         problems=["project", "repository", "repository[phabricator.callsign]"])

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
        snapshot_id = args.snapshot_id
        no_snapshot = args.no_snapshot

        cause = Cause[args.cause]

        if no_snapshot and snapshot_id:
            return error("Cannot specify snapshot with no_snapshot option")

        if not tag and args.patch_file:
            tag = 'patch'

        # 2. validate snapshot
        if snapshot_id:
            snapshot = Snapshot.query.get(snapshot_id)
            if not snapshot:
                return error("Unable to find snapshot.")
            if snapshot.status != SnapshotStatus.active:
                return error("Snapshot is in an invalid state: %s" % snapshot.status)
            for project in projects:
                plans = get_build_plans(project)
                for plan in plans:
                    plan_options = plan.get_item_options()
                    allow_snapshot = '1' == plan_options.get('snapshot.allow', '0') or plan.snapshot_plan
                    if allow_snapshot and not SnapshotImage.get(plan, snapshot_id):
                        # We want to create a build using a specific snapshot but no image
                        # was found for this plan so fail.
                        return error("Snapshot cannot be applied to %s's %s" % (project.slug, plan.label))

        # 3. find revision
        try:
            revision = identify_revision(repository, args.sha)
        except MissingRevision:
            # if the default fails, we absolutely can't continue and the
            # client should send a valid revision
            return error("Unable to find commit %s in %s." % (args.sha, repository.url),
                         problems=['sha', 'repository'])

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

        # 4. Check for patch
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

        apply_project_files_trigger = args.apply_project_files_trigger
        if apply_project_files_trigger is None:
            apply_project_files_trigger = args.apply_file_whitelist
        if apply_project_files_trigger is None:
            if is_commit_build:
                apply_project_files_trigger = False
            else:
                apply_project_files_trigger = True

        if apply_project_files_trigger:
            if patch:
                diff_parser = DiffParser(patch.diff)
                files_changed = diff_parser.get_changed_files()
            elif revision:
                try:
                    files_changed = _get_revision_changed_files(repository, revision)
                except MissingRevision:
                    return error("Unable to find commit %s in %s." % (args.sha, repository.url),
                                 problems=['sha', 'repository'])
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
            # 5. apply project whitelist as appropriate
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

            # 6. apply file whitelist as appropriate
            diff = None
            if patch is not None:
                diff = patch.diff
            try:
                if (
                    apply_project_files_trigger and
                    files_changed is not None and
                    not files_changed_should_trigger_project(
                        files_changed, project, project_options[project.id], sha, diff)
                ):
                    logging.info('Changed files do not trigger build for project %s', project.slug)
                    continue
            except InvalidDiffError:
                # ok, the build will fail and the user will be notified.
                pass
            except ProjectConfigError:
                author_name = '(Unknown)'
                if author:
                    author_name = author.name
                logging.error('Project config for project %s is not in a valid format. Author is %s.', project.slug, author_name, exc_info=True)

            # 7. create/ensure build
            if args.ensure_only:
                potentials = list(Build.query.filter(
                    Build.project_id == project.id,
                    Build.source.has(revision_sha=sha, patch=patch),
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
                        cause=cause,
                        snapshot_id=snapshot_id,
                        no_snapshot=no_snapshot
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
                    cause=cause,
                    snapshot_id=snapshot_id,
                    no_snapshot=no_snapshot
                ))

        return self.respond(builds)
