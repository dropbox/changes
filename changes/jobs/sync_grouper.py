import logging
import requests
import urlparse

from flask import current_app
from typing import Iterable, Set  # NOQA

from changes.config import db, statsreporter
from changes.models.user import User


logger = logging.getLogger('grouper.sync')


def sync_grouper():
    # type: () -> None
    """This function is meant as a Celery task. It connects to Grouper, gets
    all users who should be admin, and makes sure that those users and only
    those users are admin.
    """
    try:
        admin_emails = _get_admin_emails_from_grouper()
        _sync_admin_users(admin_emails)
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
    """
    url = urlparse.urljoin(current_app.config['GROUPER_API_URL'],
                           '/permissions/{}'.format(current_app.config['GROUPER_PERMISSIONS_ADMIN']))
    groups = requests.get(url).json()['data']['groups']

    admin_users = set()
    for _, group in groups.iteritems():
        for email, user in group['users'].iteritems():
            if user['rolename'] not in current_app.config['GROUPER_EXCLUDED_ROLES']:
                admin_users.add(email)
    return admin_users


def _sync_admin_users(admin_emails):
    # type: (Iterable[str]) -> None
    """Take a look at the Changes user database. Every user with email in
    `admin_emails` should become a Changes admin, and every user already
    an admin whose email is not in `admin_emails` will have their
    admin privileges revoked.

    Args:
        admin_emails (iterable[basestring]): an iterable of usernames of
            people who should be admin.
    """
    # revoke access for people who should not have admin access
    User.query.filter(
        ~User.email.in_(admin_emails),
        User.is_admin.is_(True),
    ).update({
        'is_admin': False,
    }, synchronize_session=False)

    # give access for people who should have access
    User.query.filter(
        User.email.in_(admin_emails),
        User.is_admin.is_(False),
    ).update({
        'is_admin': True,
    }, synchronize_session=False)
    db.session.commit()
