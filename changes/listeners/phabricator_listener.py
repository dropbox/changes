
import re
import urllib

from flask import current_app

from changes.config import db
from changes.constants import Result, Status
from changes.db.utils import try_create
from changes.lib import build_context_lib, build_type
from changes.lib.coverage import get_coverage_by_build_id, merged_coverage_data
from changes.models.build import Build
from changes.models.option import ItemOption
from changes.models.project import ProjectOption, ProjectOptionsHelper
from changes.models.repository import RepositoryBackend
from changes.models.source import Source
from changes.models.event import Event, EventType
from changes.models.job import Job
from changes.models.test import TestCase
from changes.utils.http import build_uri
from changes.utils.phabricator_utils import logger, PhabricatorClient, post_comment
from changes.vcs.git import GitVcs
from changes.vcs.hg import MercurialVcs
from sqlalchemy.orm import joinedload

# Copied from api/serializer/models/repository.py
DEFAULT_BRANCHES = {
    RepositoryBackend.git: GitVcs.get_default_revision(),
    RepositoryBackend.hg: MercurialVcs.get_default_revision(),
    RepositoryBackend.unknown: ''
}


def get_options(project_id):
    return dict(
        db.session.query(
            ProjectOption.name, ProjectOption.value
        ).filter(
            ProjectOption.project_id == project_id,
            ProjectOption.name.in_([
                'phabricator.notify',
                'phabricator.coverage',
            ])
        )
    )


def get_repo_options(repo_id):
    return dict(
        db.session.query(
            ItemOption.name, ItemOption.value
        ).filter(
            ItemOption.item_id == repo_id,
            ItemOption.name.in_([
                'phabricator.callsign',
            ])
        )
    )


def post_diff_coverage(revision_id, coverage, phab):
    # See https://secure.phabricator.com/T9529
    revisions = phab.post('differential.query', ids=[revision_id])
    if not revisions:
        logger.warn("post_diff_coverage: No data for revision D%s", revision_id)
        return
    rev = revisions[0]
    key = 'arcanist.unit'
    target_map = phab.post('harbormaster.queryautotargets',
                          objectPHID=rev['activeDiffPHID'], targetKeys=[key])['targetMap']
    phid = target_map.get(key)
    if phid is None:
        logger.warn("post_diff_coverage: No target PHID for revision D%s", revision_id)
        return
    unit = [dict(name="Coverage results from Changes for %d files" % len(coverage),
                 result='pass', coverage=coverage)]
    phab.post('harbormaster.sendmessage', buildTargetPHID=phid, type='work', unit=unit)


def commit_details(source):
    repo = source.repository
    if not repo:
        return None, None, None
    options = get_repo_options(repo.id)
    callsign = options.get('phabricator.callsign')
    default_branch = DEFAULT_BRANCHES[repo.backend]
    branches = source.revision.branches
    if not branches:
        branch = default_branch
    elif len(branches) == 1:
        branch = branches[0]
    elif default_branch in branches:
        branch = default_branch
    else:
        # Don't know which of several branches to choose; the default branch isn't listed.
        logger.warn(
            "commit_details: ambiguous branching (default branch %r, revision branches %r)",
            branch, branches)
        return None, None, None
    return callsign, branch, source.revision_sha


def parse_revision_id(message):
    """Parse the revision id out of a commit message"""

    match = re.search('^Differential Revision:.*/D(\d+)$', message, re.MULTILINE)
    return int(match.group(1)) if match else None


def post_commit_coverage(callsign, branch, commit, coverage, phab):
    phab_repos = phab.post('repository.query', callsigns=[callsign])
    if not phab_repos:
        return
    phid = phab_repos[0]['phid']
    # Doing it
    phab.post('diffusion.updatecoverage',
              repositoryPHID=phid,
              branch=branch,
              commit=commit,
              coverage=coverage,
              mode='update')


def _comment_posted_for_collection_of_build(build):
    event = try_create(Event, where={
        'type': EventType.phabricator_comment,
        'item_id': build.collection_id,
        'data': {
            'triggering_build_id': build.id.hex,
        }
    })
    return not event


def build_finished_handler(build_id, **kwargs):
    build = Build.query.get(build_id)
    if build is None:
        return

    if build_type.is_arc_test_build(build):
        # 'arc test' builds have an associated Phabricator diff, but
        # aren't necessarily for the diff under review, so we don't
        # want to notify with them.
        return

    options = get_options(build.project_id)
    if options.get('phabricator.notify', '0') != '1':
        return

    target = build.target
    is_diff_build = build_type.is_phabricator_diff_build(build)
    is_commit_build = build_type.is_initial_commit_build(build)

    phab = PhabricatorClient()

    if options.get('phabricator.coverage', '0') == '1' and (is_diff_build or is_commit_build):
        coverage = merged_coverage_data(get_coverage_by_build_id(build_id))
        if coverage:
            if is_diff_build:
                logger.info("Posting coverage to %s", target)
                post_diff_coverage(target[1:], coverage, phab)
            elif is_commit_build:
                # commits update diffs in phabricator, so post the coverage there too
                revision_id = parse_revision_id(build.message)
                if revision_id:
                    post_diff_coverage(revision_id, coverage, phab)

                callsign, branch, commit = commit_details(build.source)
                if callsign and commit:
                    logger.info("Posting coverage to %s, %s, %s", callsign, branch, commit)
                    post_commit_coverage(callsign, branch, commit, coverage, phab)

    if not is_diff_build:
        # Not a diff build
        return

    builds = list(
        Build.query.filter(Build.collection_id == build.collection_id))

    # Filter collection of builds down to only consider/report builds for
    # projects with phabricator.notify set.
    options = ProjectOptionsHelper.get_options([b.project for b in builds], ['phabricator.notify'])
    builds = [b for b in builds if options[b.project.id].get('phabricator.notify', '0') == '1']

    # Exit if there are no builds for the given build_id, or any build hasn't
    # finished.
    if not builds or any(map(lambda b: b.status != Status.finished, builds)):
        return

    # if comment has already been posted for this set of builds, don't do anything
    if _comment_posted_for_collection_of_build(build):
        return

    context = build_context_lib.get_collection_context(builds)

    message = '\n\n'.join([_get_message_for_build_context(x) for x in context['builds']])

    post_comment(target, message, phab)


def _get_message_for_build_context(build_context):
    build = build_context['build']
    result = build.result
    if result == Result.passed:
        result_image = '{icon check, color=green}'
    elif result == Result.failed:
        result_image = '{icon times, color=red}'
    else:
        result_image = '{icon question, color=orange}'
    safe_slug = urllib.quote_plus(build.project.slug)
    message = u'{project} build {result} {image} ([results]({link})).'.format(
        project=build.project.name,
        image=result_image,
        result=unicode(build.result),
        link=build_uri('/find_build/{0}/'.format(build.id.hex))
    )

    test_failures = [t['test_case'] for t in build_context['failing_tests']]

    if build_context['failing_tests_count'] > 0:
        message += get_test_failure_remarkup(build, test_failures)
    return message


def get_test_failures_in_base_commit(build):
    """
    Returns: None if there was a problem locating the base commit or base build.
        Otherwise a dictionary of test names that failed in the most recent base
        build.
    """
    commit_sources = [s.id for s in Source.query.filter(
            Source.revision_sha == build.source.revision_sha) if s.is_commit()]

    base_builds = Build.query.filter(
        Build.source_id.in_(commit_sources),
        Build.project_id == build.project_id
    )
    if not list(base_builds):
        logger.info("Unable to find base build for %s",
                    build.source.revision_sha)
        return None

    jobs = list(Job.query.filter(
        Job.build_id.in_([b.id for b in base_builds])
    ))
    if not list(jobs):
        logger.info("Unable to find jobs matching build for %s",
                    build.source.revision_sha)
        return None

    test_failures = TestCase.query.options(
        joinedload('job', innerjoin=True),
    ).filter(
        TestCase.job_id.in_([j.id for j in jobs]),
        TestCase.result == Result.failed,
    )

    return {test.name for test in test_failures}


def _generate_remarkup_table_for_tests(build, tests):
    num_failures = len(tests)
    did_truncate = False
    max_shown = current_app.config.get('MAX_SHOWN_ITEMS_PER_BUILD_PHABRICATOR', 10)
    if num_failures > max_shown:
        tests = tests[:max_shown]
        did_truncate = True

    table = ['|Test Name | Package|',
             '|--|--|']
    for test in tests:
        pkg = test.package
        name = test.name
        if pkg and name.startswith(pkg):
            name = name[len(pkg) + 1:]

        test_link = build_uri('/build_test/{0}/{1}/'.format(
            build.id.hex,
            test.id.hex,
        ))
        table = table + ['|[%s](%s)|%s|' % (name, test_link, pkg)]

    if did_truncate:
        table += ['|...more...|...|']

    return '\n'.join(table)


def get_test_failure_remarkup(build, tests):
    safe_slug = urllib.quote_plus(build.project.slug)

    base_commit_failures = get_test_failures_in_base_commit(build)
    if base_commit_failures is None:
        total_failures = [t for t in tests]
        failures_in_parent = []
        message = ' There were a total of ' \
                  '{num_failures} [test failures]({link}), but we could not ' \
                  'determine if any of these tests were previously failing.'.format(
                      num_failures=len(tests),
                      link=build_uri('/build_tests/{0}/'.format(build.id.hex))
                  )
        message += '\n\n**All failures ({failure_count}):**\n'.format(
            failure_count=len(total_failures)
        )
        message += _generate_remarkup_table_for_tests(build, total_failures)

    else:
        new_failures = [t for t in tests if t.name not in base_commit_failures]
        failures_in_parent = [t for t in tests if t.name in base_commit_failures]
        message = ' There were {new_failures} new [test failures]({link})'.format(
            new_failures=len(new_failures),
            link=build_uri('/build_tests/{0}/'.format(build.id.hex))
        )

        if new_failures:
            message += '\n\n**New failures ({new_failure_count}):**\n'.format(
                new_failure_count=len(new_failures)
            )
            message += _generate_remarkup_table_for_tests(build, new_failures)

    if failures_in_parent:
        message += '\n\n**Failures in parent revision ({parent_failure_count}):**\n'.format(
            parent_failure_count=len(failures_in_parent)
        )
        message += _generate_remarkup_table_for_tests(build, failures_in_parent)
    return message
