from __future__ import absolute_import

from flask import current_app

import json
import logging
import requests

from .base import ArtifactHandler
from typing import Any, List, Dict  # NOQA


# Maximum number of entries we allow before considering the analytics file to be
# dangerously large and marking it malformed. Arbitrary, but avoids implicitly supporting
# arbitrarily large data.
MAX_ENTRIES = 5000


class AnalyticsJsonHandler(ArtifactHandler):
    """
    Artifact handler for analytics files. Makes sure their contents are valid.
    """
    FILENAMES = ('CHANGES_ANALYTICS.json', '*.CHANGES_ANALYTICS.json')

    def process(self, fp):
        allowed_tables = current_app.config.get('ANALYTICS_PROJECT_TABLES', [])
        try:
            contents = json.load(fp)
        except ValueError:
            # Warning here because malformed might be an infrastructural issue.
            self.logger.warning('Failed to parse analytics json; (build=%s, step=%s)',
                                self.step.job.build_id.hex, self.step.id.hex, exc_info=True)
            self.report_malformed()
            return
        try:
            _validate_structure(contents, allowed_tables)
        except ValueError:
            self.logger.warning('Invalid analytics JSON; (build=%s, step=%s)',
                                self.step.job.build_id.hex, self.step.id.hex, exc_info=True)
            self.report_malformed()
            return
        table = contents['table']
        entries = contents['entries']
        for ent in entries:
            ent['jobstep_id'] = self.step.id.hex

        url = current_app.config.get('ANALYTICS_PROJECT_POST_URL')
        if not url:
            self.logger.warning('Got analytics JSON but no POST url configured (build=%s, step=%s)',
                                self.step.job.build_id.hex, self.step.id.hex)
            return
        _post_analytics_data(url, table, entries)


def _validate_structure(contents, allowed_tables):
    # type: (Any, List[str]) -> None
    if not isinstance(contents, dict):
        raise ValueError("Must be dict")
    table = contents.get('table')
    if not table:
        raise ValueError("'table' must be specified")
    if table not in allowed_tables:
        raise ValueError("'%s' is not an allowed table (allowed: %s)".format(table, ','.join(allowed_tables)))
    entries = contents.get('entries')
    if not isinstance(entries, list):
        raise ValueError("'entries' must be a list")
    if len(entries) > MAX_ENTRIES:
        raise ValueError("Too many entries")
    if not all(isinstance(e, dict) for e in entries):
        raise ValueError("Entries must all be JSON objects")
    # All good.


def _post_analytics_data(url, table, data):
    # type: (str, str, List[Dict[str, Any]]) -> None
    """
    Args:
        url: HTTP URL to POST to.
        table: Destination table.
        data: Records to POST as JSON.
    """
    try:
        resp = requests.post(url, params={'source': table},
                             headers={'Content-Type': 'application/json'},
                             data=json.dumps(data), timeout=10)
        resp.raise_for_status()
    except Exception:
        logging.exception("Failed to post project data to Analytics")
