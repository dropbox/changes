"""Posts JSON with basic information for each completed build to the URL specified
in the config variable ANALYTICS_POST_URL, if that value is set.

The data posted to ANALYTICS_POST_URL will be a JSON array of objects, with each
object representing a completed build.
"""

import logging
import json
import re
import requests
from sqlalchemy import distinct
from collections import defaultdict
from datetime import datetime

from flask import current_app

from changes.config import db, statsreporter
from changes.constants import Result
from changes.models import Build, FailureReason, Job, JobStep, LogSource, LogChunk
from changes.experimental import categorize

logger = logging.getLogger('analytics_notifier')


def _datetime_to_timestamp(dt):
    """Convert a datetime to unix epoch time in seconds."""
    return int((dt - datetime.utcfromtimestamp(0)).total_seconds())


_REV_URL_RE = re.compile(r'^\s*Differential Revision:\s+(http.*/D[0-9]+)\s*$', re.MULTILINE)


def _get_phabricator_revision_url(build):
    """Returns the Phabricator Revision URL for a Build.

    Args:
      build (Build): The Build.

    Returns:
      A str with the Phabricator Revision URL, or None if we couldn't find one (or found
      multiple).
    """
    source_data = build.source.data or {}
    rev_url = source_data.get('phabricator.revisionURL')
    if rev_url:
        return rev_url
    if build.message:
        matches = _REV_URL_RE.findall(build.message)
        # only return if there's a clear choice.
        if matches and len(matches) == 1:
            return matches[0]
    return None


def _get_build_failure_reasons(build):
    """Return the names of all the FailureReasons associated with a build.
    Args:
        build (Build): The build to return reasons for.
    Returns:
        list: A sorted list of the distinct FailureReason.reason values associated with
        the build.
    """
    failure_reasons = [r for r, in db.session.query(
                distinct(FailureReason.reason)
            ).filter(
                FailureReason.build_id == build.id
            ).all()]
    # The order isn't particularly meaningful; the sorting is primarily
    # to make the same set of reasons reliably result in the same JSON.
    return sorted(failure_reasons)


def maybe_ts(dt):
    if dt:
        return _datetime_to_timestamp(dt)
    return None


def build_finished_handler(build_id, **kwargs):
    url = current_app.config.get('ANALYTICS_POST_URL')
    if not url:
        return
    build = Build.query.get(build_id)
    if build is None:
        return

    failure_reasons = _get_build_failure_reasons(build)

    data = {
        'build_id': build.id.hex,
        'result': unicode(build.result),
        'project_slug': build.project.slug,
        'is_commit': bool(build.source.is_commit()),
        'label': build.label,
        'number': build.number,
        'duration': build.duration,
        'target': build.target,
        'date_created': maybe_ts(build.date_created),
        'date_started': maybe_ts(build.date_started),
        'date_finished': maybe_ts(build.date_finished),
        # Revision URL rather than just revision id because the URL should
        # be globally unique, whereas the id is only certain to be unique for
        # a single Phabricator instance.
        'phab_revision_url': _get_phabricator_revision_url(build),
        'failure_reasons': failure_reasons,
    }
    if build.author:
        data['author'] = build.author.email

    post_analytics_data(url, [data])


def post_analytics_data(url, data):
    """
    Args:
        url (str): HTTP URL to POST to.
        data (list): Records to POST as JSON.
    """
    try:
        resp = requests.post(url, headers={'Content-Type': 'application/json'}, data=json.dumps(data))
        resp.raise_for_status()
        # Should probably retry here so that transient failures don't result in
        # missing data.
    except Exception:
        logger.exception("Failed to post to Analytics")


def job_finished_handler(job_id, **kwargs):
    job = Job.query.get(job_id)
    if job is None:
        return

    tags_by_step = _categorize_step_logs(job)

    url = current_app.config.get('ANALYTICS_JOBSTEP_POST_URL')
    if not url:
        return
    records = []
    failure_reasons_by_jobstep = _get_job_failure_reasons_by_jobstep(job)
    for jobstep in JobStep.query.filter(JobStep.job == job):
        data = {
                'jobstep_id': jobstep.id.hex,
                'job_id': jobstep.job_id.hex,
                'phase_id': jobstep.phase_id.hex,
                'build_id': job.build_id.hex,
                'label': jobstep.label,
                'result': unicode(jobstep.result),
                'date_started': maybe_ts(jobstep.date_started),
                'date_finished': maybe_ts(jobstep.date_finished),
                'date_created': maybe_ts(jobstep.date_created),
                # jobstep.data is a changes.db.types.json.MutableDict.
                # It is not directly jsonable but its value should be a jsonable dict.
                'data': jobstep.data.value,
                'log_categories': sorted(list(tags_by_step[jobstep.id])),
                'failure_reasons': failure_reasons_by_jobstep[jobstep.id],
                # TODO: Node? Duration (to match build, for efficiency)?
        }
        records.append(data)
    post_analytics_data(url, records)


def _categorize_step_logs(job):
    """
    Args:
        job (Job): The Job to categorize logs for.
    Returns:
        Dict[UUID, Set[str]]: Mapping from JobStep ID to the categories observed for its logs.
    """
    tags_by_step = defaultdict(set)
    rules = _get_rules()
    if rules:
        for ls in _get_failing_log_sources(job):
            logdata = _get_log_data(ls)
            tags, applicable = categorize.categorize(job.project.slug, rules, logdata)
            tags_by_step[ls.step_id].update(tags)
            _incr("failing-log-processed")
            if not tags and applicable:
                _incr("failing-log-uncategorized")
                logger.warning("Uncategorized log", extra={
                    # Supplying the 'data' this way makes it available in log handlers
                    # like Sentry while keeping the warnings grouped together.
                    # See https://github.com/getsentry/raven-python/blob/master/docs/integrations/logging.rst#usage
                    # for Sentry's interpretation.
                    'data': {
                        'logsource.id': ls.id.hex,
                        'log.url': _log_uri(ls),
                    }
                })
            else:
                for tag in tags:
                    _incr("failing-log-category-{}".format(tag))
    return tags_by_step


def _get_job_failure_reasons_by_jobstep(job):
    """Return dict mapping jobstep ids to names of all associated FailureReasons.
    Args:
        job (Job): The job to return failure reasons for.
    Returns:
        dict: A dict mapping from jobstep id to a sorted list of failure reasons
    """
    reasons = [r for r in db.session.query(
                FailureReason.reason, FailureReason.step_id
            ).filter(
                FailureReason.job_id == job.id
            ).all()]

    reasons_by_jobsteps = defaultdict(list)
    for reason in reasons:
        reasons_by_jobsteps[reason.step_id].append(reason.reason)

    # The order isn't particularly meaningful; the sorting is primarily
    # to make the same set of reasons reliably result in the same JSON.
    for step_id in reasons_by_jobsteps:
        reasons_by_jobsteps[step_id].sort()
    return reasons_by_jobsteps


def _get_failing_log_sources(job):
    return list(LogSource.query.filter(
        LogSource.job_id == job.id,
    ).join(
        JobStep, LogSource.step_id == JobStep.id,
    ).filter(
        JobStep.result.in_([Result.failed, Result.infra_failed]),
    ).order_by(JobStep.date_created))


def _get_log_data(source):
    queryset = LogChunk.query.filter(
        LogChunk.source_id == source.id,
    ).order_by(LogChunk.offset.asc())
    return ''.join(l.text for l in queryset)


def _get_rules():
    """Return the current rules to be used with categorize.categorize.
    NB: Reloads the rules file at each call.
    """
    rules_file = current_app.config.get('CATEGORIZE_RULES_FILE')
    if not rules_file:
        return None
    return categorize.load_rules(rules_file)


def _log_uri(logsource):
    """
    Args:
        logsource (LogSource): The LogSource to return URI for.

    Returns:
        str with relative URI of the provided LogSource.
    """
    job = logsource.job
    build = job.build
    project = build.project
    return "/projects/{}/builds/{}/jobs/{}/logs/{}/".format(
            project.slug, build.id.hex, job.id.hex, logsource.id.hex)


def _incr(name):
    """Helper to increments a stats counter.
    Mostly exists to ease mocking in tests.
    Args:
        name (str): Name of counter to increment.
    """
    statsreporter.stats().incr(name)
