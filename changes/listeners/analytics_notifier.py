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
from uuid import UUID  # NOQA

from flask import current_app
from typing import Any, Dict, List, Tuple, Union  # NOQA

from changes.config import db, statsreporter
from changes.constants import Result
from changes.models.build import Build
from changes.models.job import Job
from changes.models.jobstep import JobStep
from changes.models.log import LogChunk, LogSource
from changes.models.failurereason import FailureReason
from changes.models.itemstat import ItemStat
from changes.experimental import categorize

logger = logging.getLogger('analytics_notifier')


def _datetime_to_timestamp(dt):
    # type: (datetime) -> int
    """Convert a datetime to unix epoch time in seconds."""
    return int((dt - datetime.utcfromtimestamp(0)).total_seconds())


_REV_URL_RE = re.compile(r'^\s*Differential Revision:\s+(http.*/D[0-9]+)\s*$', re.MULTILINE)


def _get_phabricator_revision_url(build):
    # type: (Build) -> str
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
    # type: (Build) -> List[str]
    """Return the names of all the FailureReasons associated with a build.
    Args:
        build (Build): The build to return reasons for.
    Returns:
        list: A sorted list of the distinct FailureReason.reason values associated with
        the build.
    """
    failure_reasons = [r for r, in db.session.query(
                distinct(FailureReason.reason)
            ).join(
                JobStep, JobStep.id == FailureReason.step_id,
            ).filter(
                FailureReason.build_id == build.id,
                JobStep.replacement_id.is_(None),
            ).all()]
    # The order isn't particularly meaningful; the sorting is primarily
    # to make the same set of reasons reliably result in the same JSON.
    return sorted(failure_reasons)


def maybe_ts(dt):
    # type: (datetime) -> Union[int, None]
    if dt:
        return _datetime_to_timestamp(dt)
    return None


def build_finished_handler(build_id, **kwargs):
    # type: (UUID, **Any) -> None
    url = current_app.config.get('ANALYTICS_POST_URL')
    if not url:
        return
    build = Build.query.get(build_id)
    if build is None:
        return

    failure_reasons = _get_build_failure_reasons(build)

    jobsteps_replaced = JobStep.query.join(
        Job, Job.id == JobStep.job_id,
    ).filter(
        Job.build_id == build.id,
        JobStep.replacement_id.isnot(None)
    ).count()

    sorted_tags = sorted(list(build.tags or []))

    data = {
        'build_id': build.id.hex,
        'result': unicode(build.result),
        'project_slug': build.project.slug,
        'is_commit': build.source.is_commit(),
        'label': build.label,
        'number': build.number,
        'duration': build.duration,
        'target': build.target,
        'patch_hash': build.source.revision.patch_hash,
        'date_created': maybe_ts(build.date_created),
        'date_started': maybe_ts(build.date_started),
        'date_finished': maybe_ts(build.date_finished),
        'date_decided': maybe_ts(build.date_decided),
        # Revision URL rather than just revision id because the URL should
        # be globally unique, whereas the id is only certain to be unique for
        # a single Phabricator instance.
        'phab_revision_url': _get_phabricator_revision_url(build),
        'failure_reasons': failure_reasons,
        'jobsteps_replaced': jobsteps_replaced,
        # tags is a dict rather than just a list because some analytics backends (Hive, for
        # example) handle JSON objects much more conveniently than lists.
        'tags': {'tags': sorted_tags},
        # On the other hand other analytics backends (like beta-stage fancy auto-aggregating
        # charting systems) only take strings, booleans, numbers, and dates/timestamps.
        # So make the tags a string too.
        'tags_string': ','.join(sorted_tags),
        'item_stats': _get_itemstat_dict(build.id),
    }
    if build.author:
        data['author'] = build.author.email

    post_analytics_data(url, [data])


def post_analytics_data(url, data):
    # type: (str, List[Any]) -> None
    """
    Args:
        url (str): HTTP URL to POST to.
        data (list): Records to POST as JSON.
    """
    try:
        resp = requests.post(url, headers={'Content-Type': 'application/json'},
                             data=json.dumps(data), timeout=10)
        resp.raise_for_status()
        # Should probably retry here so that transient failures don't result in
        # missing data.
    except Exception:
        logger.exception("Failed to post to Analytics")


def _get_itemstat_dict(iid):
    # type: (UUID) -> Dict[str, Any]
    """
    Args:
        iid (UUID): The ID of the item to get stats for.

    Returns:
        dict: Dictionary of stats.
    """
    return dict((s.name, s.value) for s in ItemStat.query.filter(ItemStat.item_id == iid))


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
        duration = None
        if jobstep.date_finished and jobstep.date_started:
            duration = int(round((jobstep.date_finished - jobstep.date_started).total_seconds() * 1000))
        data = {
                'jobstep_id': jobstep.id.hex,
                'job_id': jobstep.job_id.hex,
                'phase_id': jobstep.phase_id.hex,
                'build_id': job.build_id.hex,
                'label': jobstep.label,
                'project_slug': jobstep.project.slug,
                'cluster': jobstep.cluster,
                'result': unicode(jobstep.result),
                'replacement_id': jobstep.replacement_id.hex if jobstep.replacement_id else None,
                'date_started': maybe_ts(jobstep.date_started),
                'date_finished': maybe_ts(jobstep.date_finished),
                'date_created': maybe_ts(jobstep.date_created),
                # jobstep.data is a changes.db.types.json.MutableDict.
                # It is not directly jsonable but its value should be a jsonable dict.
                'data': jobstep.data.value,
                'log_categories': sorted(list(tags_by_step[jobstep.id])),
                'failure_reasons': failure_reasons_by_jobstep[jobstep.id],
                'item_stats': _get_itemstat_dict(jobstep.id),
                'duration': duration,
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
    # Restricting to matching JobStep ids when querying LogSources
    # allows us to use the LogSource.step_id index, which makes
    # the query significantly faster.
    jobstep_ids = db.session.query(JobStep.id).filter(
        JobStep.job_id == job.id,
        JobStep.result.in_([Result.failed, Result.infra_failed])
    ).subquery()
    return list(LogSource.query.filter(
        LogSource.step_id.in_(jobstep_ids),
    ).join(
        JobStep, LogSource.step_id == JobStep.id,
    ).order_by(JobStep.date_created))


def _get_log_data(source):
    queryset = LogChunk.query.filter(
        LogChunk.source_id == source.id,
    ).order_by(LogChunk.offset.asc())
    return ''.join(l.text for l in queryset)


def _get_rules():
    # type: () -> List[Tuple[str, str, str]]
    """Return the current rules to be used with categorize.categorize.
    NB: Reloads the rules file at each call.
    """
    rules_file = current_app.config.get('CATEGORIZE_RULES_FILE')
    if not rules_file:
        return None
    return categorize.load_rules(rules_file)


def _incr(name):
    # type: (str) -> None
    """Helper to increments a stats counter.
    Mostly exists to ease mocking in tests.
    Args:
        name (str): Name of counter to increment.
    """
    statsreporter.stats().incr(name)
