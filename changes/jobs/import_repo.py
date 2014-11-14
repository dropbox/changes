from __future__ import absolute_import, print_function

import logging

from datetime import datetime

from changes.config import db
from changes.models import Repository, RepositoryStatus
from changes.queue.task import tracked_task

logger = logging.getLogger('repo.sync')


@tracked_task(max_retries=None)
def import_repo(repo_id, parent=None):
    pass