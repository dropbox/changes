import logging

from flask import current_app
from fnmatch import fnmatch

from changes.api.build_index import BuildIndexAPIView
from changes.config import db
from changes.models import ItemOption, Project


logger = logging.getLogger('build_revision')


def should_build_branch(revision, allowed_branches):
    if not revision.branches:
        return True

    for branch in revision.branches:
        if any(fnmatch(branch, pattern) for pattern in allowed_branches):
            return True
    return False


def revision_created_handler(revision, **kwargs):
    project_list = list(Project.query.filter(
        Project.repository_id == revision.repository_id,
    ))
    if not project_list:
        return

    options = dict(
        db.session.query(
            ItemOption.item_id, ItemOption.value
        ).filter(
            ItemOption.item_id.in_(p.id for p in project_list),
            ItemOption.name.in_([
                'build.branch-names',
            ])
        )
    )

    for project in project_list:
        branch_names = options.get('build.branch-names', '*').split(' ')
        if not should_build_branch(revision, branch_names):
            return

        data = {
            'sha': revision.sha,
            'project': project.slug,
        }
        with current_app.test_request_context('/api/0/builds/', method='POST', data=data):
            response = BuildIndexAPIView().post()
            if isinstance(response, (list, tuple)):
                response, status = response
                if status != 200:
                    logger.error('Failed to create builds: %s' % (response,))
