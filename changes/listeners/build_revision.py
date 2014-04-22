import logging

from flask import current_app
from fnmatch import fnmatch

from changes.api.build_index import BuildIndexAPIView
from changes.config import db
from changes.models import ItemOption


logger = logging.getLogger('build_revision')


def should_build_branch(revision, allowed_branches):
    if not revision.branches:
        return True

    for branch in revision.branches:
        if any(fnmatch(branch, pattern) for pattern in allowed_branches):
            return True
    return False


def revision_created_handler(revision, **kwargs):
    options = dict(
        db.session.query(
            ItemOption.name, ItemOption.value
        ).filter(
            ItemOption.item_id == revision.repository_id,
            ItemOption.name.in_([
                'build.branch-names',
            ])
        )
    )

    if not should_build_branch(revision, options.get('build.branch-names', '*').split(' ')):
        return

    data = {
        'sha': revision.sha,
        'repository': revision.repository.url,
    }
    with current_app.test_request_context('/api/0/builds/', method='POST', data=data):
        response = BuildIndexAPIView().post()
        if isinstance(response, (list, tuple)):
            response, status = response
            if status != 200:
                logger.error('Failed to create builds: %s' % (response,))
