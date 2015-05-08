"""Runs a classifier on logs of failed jobs and reports the classifications.
The rules for the classifier are loaded from the string config variable CATEGORIZE_RULES_FILE.
If that variable isn't specified, no classification is attempted.
"""
import logging
from flask import current_app

from changes.config import statsreporter
from changes.constants import Result
from changes.models import Job, LogSource, LogChunk, JobStep
from changes.experimental import categorize


logger = logging.getLogger('log_processing')


def _get_failing_log_sources(job):
    return list(LogSource.query.filter(
        LogSource.job_id == job.id,
    ).join(
        JobStep, LogSource.step_id == JobStep.id,
    ).filter(
        JobStep.result == Result.failed,
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
            project.id.hex, build.id.hex, job.id.hex, logsource.id.hex)


def _incr(name):
    """Helper to increments a stats counter.
    Mostly exists to ease mocking in tests.
    Args:
        name (str): Name of counter to increment.
    """
    statsreporter.stats().incr(name)


def job_finished_handler(job_id, **kwargs):
    job = Job.query.get(job_id)
    if job is None:
        return

    rules = _get_rules()
    if not rules:
        return

    for ls in _get_failing_log_sources(job):
        logdata = _get_log_data(ls)
        tags, applicable = categorize.categorize(job.project.slug, rules, logdata)
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
