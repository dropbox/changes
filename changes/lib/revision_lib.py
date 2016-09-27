from typing import List  # NOQA
from uuid import UUID  # NOQA

from changes.constants import Status
from changes.lib.build_type import get_any_commit_build_filters
from changes.models.build import Build
from changes.models.revision import Revision
from changes.models.source import Source


def get_latest_finished_build_for_revision(revision_sha, project_id):
    # type: (str, UUID) -> Build
    return Build.query.join(
        Source, Build.source_id == Source.id,
    ).filter(
        Build.project_id == project_id,
        Build.status == Status.finished,
        Source.revision_sha == revision_sha,
        *get_any_commit_build_filters()
    ).order_by(
        Build.date_created.desc(),
    ).first()


def get_child_revisions(revision):
    # type: (Revision) -> List[Revision]
    return Revision.query.filter(
        Revision.repository_id == revision.repository_id,
        Revision.parents.any(revision.sha),
    ).all()
