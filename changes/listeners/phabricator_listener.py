import logging
import time
import hashlib
import json
from changes.models.job import Job
from changes.models.test import TestCase
import requests

from flask import current_app

from changes.config import db
from changes.constants import Result
from changes.models import Build, ProjectOption, Source
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
    requests.post(comment_url, comment_args)


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

    result_image = ''
    if build.result == Result.passed:
        result_image = '{icon check, color=green}'
    elif build.result == Result.failed:
        result_image = '{icon times, color=red}'
    else:
        result_image = '{icon question, color=orange}'

    message = u'{project} build {result} {image} ([results]({link})).'.format(
        project=build.project.name,
        image=result_image,
        result=unicode(build.result),
        link=build_uri('/projects/{0}/builds/{1}/'.format(build.project.slug, build.id.hex))
    )

    jobs = list(Job.query.filter(
        Job.build_id == build_id,
    ))

    test_failures = TestCase.query.options(
        joinedload('job', innerjoin=True),
        ).filter(
        TestCase.job_id.in_([j.id for j in jobs]),
        TestCase.result == Result.failed,
        ).order_by(TestCase.name.asc())
    num_test_failures = test_failures.count()

    if num_test_failures > 0:
        message += get_test_failure_remarkup(build, test_failures)

    post_comment(target, message)


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
            build.project.slug,
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

    message = ' There were {new_failures} new [test failures]({link})'.format(
        num_failures=tests.count(),
        new_failures=len(new_failures),
        link=build_uri('/projects/{0}/builds/{1}/tests/?result=failed'.format(build.project.slug, build.id.hex))
    )
    message += '\n\n'
    message += '**New failures ({new_failure_count}):**\n'.format(
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
