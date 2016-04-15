"""Posts data about completed events through statsreporter.
"""

import re
from typing import Any, List
from uuid import UUID

from changes.config import statsreporter
from changes.constants import Result
from changes.models.build import Build


def build_finished_handler(build_id, **kwargs):
    # type: (UUID, **Any) -> None
    for key in build_finished_metrics(build_id):
        statsreporter.stats().incr(key)


def build_finished_metrics(build_id):
    # type: (UUID) -> List[str]
    keys = []  # type: List[str]

    build = Build.query.get(build_id)
    if build is None:
        return keys

    # For these metrics, only count builds triggered on commits in master.
    if list(build.tags or ()) != ['commit']:
        return keys

    # This corresponds to Stats._KEY_RE in statsreporter.
    # Or broadly to just not using complicated names.
    slug_mangled = re.sub('[^A-Za-z0-9_-]', '_', build.project.slug)

    # For computing metrics like failure rates, generally we want
    #   aborted -> not counted at all
    #   passed -> counted in denominator
    #   failed or infra_failed -> counted in numerator and denominator
    #  (unknown shouldn't be possible for a finished build)
    #  (skipped and quarantine_* shouldn't be possible for builds, only tests)
    if build.result != Result.aborted:
        keys.append('build_complete_commit_{}'.format(slug_mangled))
        if build.result != Result.passed:
            keys.append('build_failed_commit_{}'.format(slug_mangled))

    return keys
