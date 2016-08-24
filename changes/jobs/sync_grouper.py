import logging
import requests
import urlparse

from flask import current_app
from typing import Dict, Iterable, Set  # NOQA

from changes.config import db, statsreporter
from changes.db.utils import create_or_update
from changes.models.user import User


logger = logging.getLogger('grouper.sync')


class GrouperApiError(Exception):
    pass


def sync_grouper():
    # type: () -> None
    """This function is meant as a Celery task. It connects to Grouper, and
    does two sets of syncs:
    - global admin
    - project-level admins
    """
    try:
        admin_emails = _get_admin_emails_from_grouper()
        _sync_admin_users(admin_emails)
        project_admin_mapping = _get_project_admin_mapping_from_grouper()
        _sync_project_admin_users(project_admin_mapping)
    except Exception:
        logger.exception("An error occurred during Grouper sync.")
        statsreporter.stats().set_gauge('grouper_sync_error', 1)
        raise
    else:
        statsreporter.stats().set_gauge('grouper_sync_error', 0)


def _get_admin_emails_from_grouper():
    # type: () -> Set[str]
    """This function connects to Grouper and retrieves the list of emails of
    users with admin permission.

    Returns:
        set[basestring]: a set of emails of admin users
    Raises:
        GrouperApiError - If there is an error on returned from Grouper
    """
    url = urlparse.urljoin(current_app.config['GROUPER_API_URL'],
                           '/permissions/{}'.format(current_app.config['GROUPER_PERMISSIONS_ADMIN']))
    response = requests.get(url).json()
    if 'errors' in response:
        message = '\n'.join([x['message'] for x in response['errors']])
        raise GrouperApiError(message)
    groups = response['data']['groups']

    admin_users = set()
    for _, group in groups.iteritems():
        for email, user in group['users'].iteritems():
            if user['rolename'] not in current_app.config['GROUPER_EXCLUDED_ROLES']:
                admin_users.add(email)
    return admin_users


def _sync_admin_users(admin_emails):
    # type: (Set[str]) -> None
    """Take a look at the Changes user database. Every user with email in
    `admin_emails` should become a Changes admin, and every user already
    an admin whose email is not in `admin_emails` will have their
    admin privileges revoked. Note that if a user who should be an admin
    does not exist in the Changes database, the user is created.

    Args:
        admin_emails (iterable[basestring]): an iterable of usernames of
            people who should be admin.
    """
    # revoke access for people who should not have admin access
    assert len(admin_emails) > 0
    User.query.filter(
        ~User.email.in_(admin_emails),
        User.is_admin.is_(True),
    ).update({
        'is_admin': False,
    }, synchronize_session=False)

    # give access for people who should have access
    for email in admin_emails:
        create_or_update(User, where={
            'email': email,
        }, values={
            'is_admin': True,
        })
    db.session.commit()


def _get_project_admin_mapping_from_grouper():
    # type: () -> Dict[str, Set[str]]
    """This connects to Grouper and retrieves users with project admin
    permissions.

    Returns:
        Dict[str, Set[str]]: The mapping from emails to project patterns
            (the same ones that goes into User.project_permissions)
    Raises:
        GrouperApiError - If there is an error on returned from Grouper
    """
    url = urlparse.urljoin(current_app.config['GROUPER_API_URL'],
                           '/permissions/{}'.format(current_app.config['GROUPER_PERMISSIONS_PROJECT_ADMIN']))
    response = requests.get(url).json()
    if 'errors' in response:
        if len(response['errors']) == 1 and response['errors'][0]['code'] == 404:
            # this just means that we have not assigned any project admins on
            # grouper. Unlike with global admin, this is a totally valid
            # scenario
            return dict()
        message = '\n'.join([x['message'] for x in response['errors']])
        raise GrouperApiError(message)
    groups = response['data']['groups']
    mapping = dict()  # type: Dict[str, Set[str]]
    for _, group in groups.iteritems():
        pattern_set = set()
        for p in group['permissions']:
            if p['permission'] == current_app.config['GROUPER_PERMISSIONS_PROJECT_ADMIN']:
                # based on my inspection of Grouper API, this condition above is
                # probably always true, but let's check anyways to be confident
                pattern = p['argument']
                if len(pattern) > 0:  # an empty string = unargumented permission
                    pattern_set.add(pattern)
        if len(pattern_set) > 0:
            # this is most likely always true, unless the Grouper API somehow
            # lists a group that has nothing to do with this permission
            for email, user in group['users'].iteritems():
                if user['rolename'] not in current_app.config['GROUPER_EXCLUDED_ROLES']:
                    existing_pattern_set = mapping.get(email, set())
                    mapping[email] = existing_pattern_set.union(pattern_set)
    return mapping


def _sync_project_admin_users(project_admin_mapping):
    # type: (Dict[str, Set[str]]) -> None
    """This synchronizes the Changes user database so that only people
    in `project_admin_mapping` are project admins, and that they are
    admins only for the projects they have permissions to.  Note that
    if a user who should be a project admin does not exist in the Changes
    database, the user is created.

    Args:
        project_admin_mapping (Dict[str, Set[str]]): The mapping from
            user emails to project patterns
    """
    args = [~User.project_permissions.is_(None)]
    if len(project_admin_mapping) > 0:
        args.append(~User.email.in_(project_admin_mapping.keys()))
    User.query.filter(*args).update({
        'project_permissions': None
    }, synchronize_session=False)
    for email, project_permissions in project_admin_mapping.iteritems():
        create_or_update(User, where={
            'email': email,
        }, values={
            'project_permissions': list(project_permissions)
        })
    db.session.commit()
