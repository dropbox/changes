from __future__ import absolute_import, print_function

import logging

from datetime import datetime

from changes.config import db
from changes.jobs.signals import fire_signal
from changes.models import Repository, RepositoryStatus
from changes.queue.task import tracked_task

logger = logging.getLogger('repo.sync')


@tracked_task(max_retries=None)
def sync_repo(repo_id, continuous=True):
    pass