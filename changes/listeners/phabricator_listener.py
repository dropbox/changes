import logging
import time
import hashlib
import json

from changes.models.job import Job
from changes.models.test import TestCase

import requests
import urllib

from flask import current_app

from changes.config import db
from changes.constants import Result, Status
from changes.db.utils import try_create
from changes.lib import build_context_lib
from changes.lib.coverage import get_coverage_by_build_id, merged_coverage_data
from changes.models import Build, ItemOption, ProjectOption, RepositoryBackend, Source
from changes.models.event import Event, EventType
from changes.utils.http import build_uri
from changes.vcs.git import GitVcs
from changes.vcs.hg import MercurialVcs
from sqlalchemy.orm import joinedload

# Copied from api/serializer/models/repository.py
DEFAULT_BRANCHES = {
    RepositoryBackend.git: GitVcs.get_default_revision(),
    RepositoryBackend.hg: MercurialVcs.get_default_revision(),
    RepositoryBackend.unknown: ''
}


logger = logging.getLogger('phabricator-listener')


class Phabricator(object):
    """A poor man's Phabricator connector.

    Usage:
      p = Phabricator(username, cert, host)
      result = p.post(method_name, **kwds)

    Where:
      - method_name is the dotted method name from the Conduit docs
      - **kwds is a set of keyword args for that method

    Example:
      p.post('differential.createcomment', revision_id='123', message='hello')

    Notes:
      - Phabricator objects aren't cached.  Connecting is assumed
        to be fast and cheap.  (Not sure if it really is.)
    """

    def __init__(self, username, cert, host):
        # Must pass in stuff
        assert username and cert and host, (username, cert, host)

        # Host must be e.g. 'https://secure.phabricator.com',
        # not what's in .arcrc (like 'https://secure.phabricator.com/api/'),
        # nor a plain DNS name (like 'secure.phabricator.com').
        assert host.startswith('http') and not host.endswith('/'), host

        self.username = username
        self.cert = cert
        self.host = host

        token = int(time.time())

        connect_args = {
            'authSignature': hashlib.sha1(str(token) + cert).hexdigest(),
            'authToken': token,
            'client': 'changes-phabricator',
            'clientVersion': 1,
            'host': self.host,
            'user': self.username,
        }

        connect_url = "%s/api/conduit.connect" % self.host
        resp = requests.post(connect_url, {
            '__conduit__': True,
            'output': 'json',
            'params': json.dumps(connect_args),
        }, timeout=10)
        resp.raise_for_status()
        resp = resp.json()['result']
        self.auth_params = {
            'connectionID': resp['connectionID'],
            'sessionKey': resp['sessionKey'],
        }

    def post(self, method, timeout=10, **kwargs):
        url = "%s/api/%s" % (self.host, method)
        kwargs['__conduit__'] = self.auth_params
        args = {
            'params': json.dumps(kwargs),
            'output': 'json',
            }
        resp = requests.post(url, args, timeout=timeout)
        resp.raise_for_status()
        raw_response = resp.json()
        error_code = raw_response['error_code']
        error_info = raw_response['error_info']
        if error_code or error_info:
            raise RuntimeError('%s request error: %s, %s' % (method, error_code, error_info))
        return raw_response['result']


def make_phab(phab):
    """Pass in a Phabricator instace or None.

    Returns a Phabricator instance, or None if no phabricator
    credentials could be found.
    """
    if phab is not None:
        return phab

    # Create a connected Phabricator instance
    username = current_app.config.get('PHABRICATOR_USERNAME')
    cert = current_app.config.get('PHABRICATOR_CERT')
    host = current_app.config.get('PHABRICATOR_HOST')
    if not username or not cert or not host:
        logger.error("Couldn't find phabricator credentials; username: %s host: %s cert: %s",
                     username, host, cert)
        return None

    return Phabricator(username, cert, host)


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


def post_diff_comment(revision_id, comment, phab):
    phab.post('differential.createcomment', revision_id=revision_id, message=comment)


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
              coverage=coverage)


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

    if build.tags and 'arc test' in build.tags:
        # 'arc test' builds have an associated Phabricator diff, but
        # aren't necessarily for the diff under review, so we don't
        # want to notify with them.
        return

    options = get_options(build.project_id)
    if options.get('phabricator.notify', '0') != '1':
        return

    target = build.target
    is_diff_build = target and target.startswith(u'D')
    is_commit_build = build.source is not None and build.source.is_commit()

    phab = None

    if options.get('phabricator.coverage', '0') == '1' and (is_diff_build or is_commit_build):
        coverage = merged_coverage_data(get_coverage_by_build_id(build_id))
        if coverage:
            phab = make_phab(phab)
            if not phab:
                return
            if is_diff_build:
                logger.info("Posting coverage to %s", target)
                post_diff_coverage(target[1:], coverage, phab)
            elif is_commit_build:
                callsign, branch, commit = commit_details(build.source)
                if callsign and commit:
                    logger.info("Posting coverage to %s, %s, %s", callsign, branch, commit)
                    post_commit_coverage(callsign, branch, commit, coverage, phab)

    if not is_diff_build:
        # Not a diff build
        return

    builds = list(
        Build.query.filter(Build.collection_id == build.collection_id))

    # Exit if there are no builds for the given build_id, or any build hasn't
    # finished.
    if not builds or any(map(lambda b: b.status != Status.finished, builds)):
        return

    # if comment has already been posted for this set of builds, don't do anything
    if _comment_posted_for_collection_of_build(build):
        return

    context = build_context_lib.get_collection_context(builds)

    message = '\n\n'.join([_get_message_for_build_context(x) for x in context['builds']])

    phab = make_phab(phab)
    if phab:
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
        link=build_uri('/projects/{0}/builds/{1}/'.format(safe_slug, build.id.hex))
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

        test_link = build_uri('/projects/{0}/builds/{1}/jobs/{2}/tests/{3}/'.format(
            urllib.quote_plus(build.project.slug),
            build.id.hex,
            test.job_id.hex,
            test.id.hex
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
                      link=build_uri('/projects/{0}/builds/{1}/tests/?result=failed'.format(safe_slug, build.id.hex))
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
            link=build_uri('/projects/{0}/builds/{1}/tests/?result=failed'.format(safe_slug, build.id.hex))
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


def post_comment(target, message, phab=None):
    try:
        logger.info("Posting build results to %s", target)
        revision_id = target[1:]
        post_diff_comment(revision_id, message, phab)
    except Exception:
        logger.exception("Failed to post to target: %s", target)
