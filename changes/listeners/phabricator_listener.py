import logging
import time
import hashlib
import json
import itertools

from changes.models.job import Job
from changes.models.test import TestCase

import requests
import urllib

from flask import current_app

from changes.config import db
from changes.constants import Result, Status
from changes.db.utils import try_create
from changes.lib import build_context_lib
from changes.models import Build, ProjectOption, Source
from changes.models.event import Event, EventType
from changes.utils.http import build_uri
from sqlalchemy.orm import joinedload


logger = logging.getLogger('phabricator-listener')


def get_options(project_id):
    return dict(
        db.session.query(
            ProjectOption.name, ProjectOption.value
        ).filter(
            ProjectOption.project_id == project_id,
            ProjectOption.name.in_([
                'phabricator.notify'
            ])
        )
    )


def post_diff_comment(diff_id, comment):
    user = current_app.config.get('PHABRICATOR_USERNAME')
    host = current_app.config.get('PHABRICATOR_HOST')
    cert = current_app.config.get('PHABRICATOR_CERT')

    if not cert:
        logger.error("Couldn't find phabricator credentials user: %s host: %s cert: %s",
                     user, host, cert)
        return

    token = int(time.time())

    connect_args = {
        'authSignature': hashlib.sha1(str(token) + cert).hexdigest(),
        'authToken': token,
        'client': 'changes-phabricator',
        'clientVersion': 1,
        'host': host,
        'user': user,
    }

    connect_url = "%s/api/conduit.connect" % host
    resp = requests.post(connect_url, {
        '__conduit__': True,
        'output': 'json',
        'params': json.dumps(connect_args),
    })
    resp.raise_for_status()

    resp = json.loads(resp.content)['result']
    auth_params = {
        'connectionID': resp['connectionID'],
        'sessionKey': resp['sessionKey'],
    }

    comment_args = {
        'params': json.dumps({
            'revision_id': diff_id,
            'message': comment,
            '__conduit__': auth_params,
        }),
        'output': 'json',
    }

    comment_url = "%s/api/differential.createcomment" % host
    comment_resp = requests.post(comment_url, comment_args)
    comment_resp.raise_for_status()


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

    target = build.target
    is_diff_build = target and target.startswith(u'D')
    if not is_diff_build:
        # Not a diff build
        return

    options = get_options(build.project_id)
    if options.get('phabricator.notify', '0') != '1':
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

    post_comment(target, message)


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

    test_failures = list(itertools.chain(*[j['failing_tests'] for j in build_context['jobs']]))
    test_failures = [t['test_case'] for t in test_failures]
    num_test_failures = len(test_failures)

    if num_test_failures > 0:
        message += get_test_failure_remarkup(build, test_failures)
    return message


def get_test_failures_in_base_commit(build):
    commit_sources = [s.id for s in Source.query.filter(
            Source.revision_sha == build.source.revision_sha) if s.is_commit()]

    base_builds = Build.query.filter(
        Build.source_id.in_(commit_sources),
        Build.project_id == build.project_id
    )
    jobs = list(Job.query.filter(
        Job.build_id.in_([b.id for b in base_builds])
    ))
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
    if num_failures > 10:
        tests = tests[:10]
        did_truncate = True

    table = ['|Test Name | Package|',
             '|--|--|']
    for test in tests:
        pkg = test.package
        name = test.name
        if name.startswith(pkg):
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
    base_commit_failures = get_test_failures_in_base_commit(build)
    new_failures = [t for t in tests if t.name not in base_commit_failures]
    failures_in_parent = [t for t in tests if t.name in base_commit_failures]

    safe_slug = urllib.quote_plus(build.project.slug)
    message = ' There were {new_failures} new [test failures]({link})'.format(
        num_failures=len(tests),
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


def post_comment(target, message):
    try:
        logger.info("Posting build results to %s", target)
        revision_id = target[1:]
        post_diff_comment(revision_id, message)
    except Exception:
        logger.exception("Failed to post to target: %s", target)
