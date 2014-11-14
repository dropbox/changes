from flask import current_app

from changes.artifacts import manager
from changes.backends.base import UnrecoverableException
from changes.constants import Result
from changes.models import Artifact, JobPlan
from changes.queue.task import tracked_task


@tracked_task
def sync_artifact(artifact_id=None, **kwargs):
    pass