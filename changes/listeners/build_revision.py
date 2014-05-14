import logging

from collections import defaultdict
from flask import current_app
from fnmatch import fnmatch

from changes.api.build_index import BuildIndexAPIView
from changes.config import db
from changes.models import ItemOption, Project


logger = logging.getLogger('build_revision')


def should_build_branch(revision, allowed_branches):
    if not revision.branches and '*' in allowed_branches:
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

    options_query = db.session.query(
        ItemOption.item_id, ItemOption.name, ItemOption.value
    ).filter(
        ItemOption.item_id.in_(p.id for p in project_list),
        ItemOption.name.in_([
            'build.branch-names',
            'build.commit-trigger',
        ])
    )

    options = defaultdict(dict)
    for project_id, option_name, option_value in options_query:
        options[project_id][option_name] = option_value

    for project in project_list:
        if options[project.id].get('build.commit-trigger', '1') != '1':
            continue

        branch_names = filter(bool, options[project.id].get('build.branch-names', '*').split(' '))
        if not should_build_branch(revision, branch_names):
            continue

        data = {
            'sha': revision.sha,
            'project': project.slug,
        }
        with current_app.test_request_context('/api/0/builds/', method='POST', data=data):
            try:
                response = BuildIndexAPIView().post()
            except Exception:
                logger.exception('Failed to create build: %s' % (response,))
            else:
                if isinstance(response, (list, tuple)):
                    response, status = response
                    if status != 200:
                        logger.error('Failed to create build: %s' % (response,))
