from itertools import chain, imap

from flask import current_app

from changes.api.build_details import get_parents_last_builds
from changes.constants import Result
from changes.models.job import Job
from changes.models.jobstep import JobStep
from changes.models.log import LogSource, LogChunk
from changes.models.test import TestCase
from changes.utils.http import build_uri


def _get_project_uri(build):
    return '/projects/{}/'.format(build.project.slug)


def _get_source_uri(build, source):
    return '{}sources/{}/'.format(_get_project_uri(build), source.id.hex)


def _get_parent_uri(build, source):
    return '{}commits/{}/'.format(_get_project_uri(build), source.revision_sha)


def _get_build_uri(build):
    return '{}builds/{}/'.format(_get_project_uri(build), build.id.hex)


def _get_job_uri(job):
    return '{}jobs/{}/'.format(_get_build_uri(job.build), job.id.hex)


def _get_test_case_uri(test_case):
    return '{}tests/{}/'.format(_get_job_uri(test_case.job), test_case.id.hex)


def _get_log_uri(log_source):
    return '{}logs/{}/'.format(_get_job_uri(log_source.job), log_source.id.hex)


def _aggregate_count(items, key):
    return sum(map(lambda item: item[key], items))


def get_collection_context(builds):
    """
    Given a non-empty list of finished builds, returns a context for
    rendering the build results.
    """

    def sort_builds(builds_context):
        result_priority_order = (
            Result.passed,
            Result.skipped,
            Result.unknown,
            Result.aborted,
            Result.infra_failed,
            Result.failed,
        )

        return sorted(
            builds_context,
            key=lambda build: (
                result_priority_order.index(build['build'].result),
                build['failing_tests_count'],
                build['failing_logs_count']
            ),
            reverse=True
        )

    builds_context = sort_builds(map(_get_build_context, builds))
    if all(map(lambda build: build['is_passing'], builds_context)):
        result = Result.passed
    elif any(imap(lambda build: build['is_failing'], builds_context)):
        result = Result.failed
    else:
        result = Result.unknown

    build = builds[0]
    target, target_uri = _get_build_target(build)

    date_created = min([_build.date_created for _build in builds])

    return {
        'title': _get_title(target, build.label, result),
        'builds': builds_context,
        'result': result,
        'target_uri': target_uri,
        'target': target,
        'label': build.label,
        'date_created': date_created,
        'author': build.author,
        'commit_message': build.message or '',
        'failing_tests_count': _aggregate_count(builds_context, 'failing_tests_count'),
    }


def _get_title(target, label, result):
    # Use the first label line for multi line labels.
    if label:
        lines = label.splitlines()
        if len(lines) > 1:
            label = u"{}...".format(lines[0])

    format_dict = {
        'target': target,
        'label': label,
        'verb': str(result).lower(),
    }

    if target:
        return u"{target} {verb} - {label}".format(**format_dict)
    else:
        return u"Build {verb} - {label}".format(**format_dict)


def _get_build_target(build):
    """
    Returns the build's target and target uri (normally a phabricator
    revision and diff url).
    """
    source_data = build.source.data or {}
    phabricator_rev_id = source_data.get('phabricator.revisionID')
    phabricator_uri = source_data.get('phabricator.revisionURL')

    if phabricator_rev_id and phabricator_uri:
        target = 'D{}'.format(phabricator_rev_id)
        target_uri = phabricator_uri
    else:
        # TODO: Make sure that the phabricator source data is present to
        # make this obsolete.
        target = None
        target_uri = build_uri(_get_source_uri(build, build.source))
    return target, target_uri


def _get_build_context(build, get_parent=True):
    jobs = list(Job.query.filter(Job.build_id == build.id))
    jobs_context = map(_get_job_context, jobs)

    parent_build_context = None
    if get_parent:
        parent_build = get_parents_last_builds(build)
        if parent_build:
            parent_build_context = _get_build_context(
                parent_build[0], get_parent=False)

    return {
        'build': build,
        'parent_build': parent_build_context,
        'jobs': jobs_context,
        'uri': build_uri(_get_build_uri(build)),
        'is_passing': build.result == Result.passed,
        'is_failing': build.result == Result.failed,
        'result_string': str(build.result).lower(),
        'failing_tests': list(chain(*[j['failing_tests'] for j in jobs_context])),
        'failing_tests_count': _aggregate_count(jobs_context, 'failing_tests_count'),
        'failing_logs_count': _aggregate_count(jobs_context, 'failing_logs_count'),
    }


def _get_job_context(job):
    def get_job_failing_tests(job):
        failing_tests = TestCase.query.filter(
            TestCase.job_id == job.id,
            TestCase.result == Result.failed,
        ).order_by(TestCase.name.asc())

        failing_tests = [
            {
                'test_case': test_case,
                'uri': build_uri(_get_test_case_uri(test_case)),
            } for test_case in failing_tests
        ]
        failing_tests_count = len(failing_tests)

        return failing_tests, failing_tests_count

    def get_job_failing_log_sources(job):
        failing_log_sources = LogSource.query.join(
            JobStep, LogSource.step_id == JobStep.id,
        ).filter(
            JobStep.result == Result.failed,
            JobStep.job_id == job.id,
        ).order_by(JobStep.date_created)

        failing_logs = [
            {
                'text': _get_log_clipping(
                    log_source, max_size=5000, max_lines=25),
                'name': log_source.name,
                'uri': build_uri(_get_log_uri(log_source)),
            } for log_source in failing_log_sources if not log_source.is_infrastructural()
        ]
        failing_log_sources_count = len(failing_logs)

        return failing_logs, failing_log_sources_count

    failing_tests, failing_tests_count = get_job_failing_tests(job)
    failing_logs, failing_logs_count = get_job_failing_log_sources(job)

    context = {
        'job': job,
        'uri': build_uri(_get_job_uri(job)),
        'failing_tests': failing_tests,
        'failing_tests_count': len(failing_tests),
        'failing_logs': failing_logs,
        'failing_logs_count': len(failing_logs),
    }

    return context


def _get_log_clipping(logsource, max_size=5000, max_lines=25):
    if logsource.in_artifact_store:
        # We don't yet get clippings for ArtifactStore logs.
        return ""
    queryset = LogChunk.query.filter(
        LogChunk.source_id == logsource.id,
    )
    tail = queryset.order_by(LogChunk.offset.desc()).limit(1).first()
    # in case logsource has no LogChunks
    if tail is None:
        current_app.logger.warning('LogSource (id=%s) had no LogChunks', logsource.id.hex)
        return ""

    chunks = list(queryset.filter(
        (LogChunk.offset + LogChunk.size) >= max(tail.offset - max_size, 0),
    ).order_by(LogChunk.offset.asc()))

    clipping = ''.join(l.text for l in chunks).strip()[-max_size:]
    # only return the last 25 lines
    clipping = '\r\n'.join(clipping.splitlines()[-max_lines:])

    return clipping
