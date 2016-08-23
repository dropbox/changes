import mock
import pytest
import responses
import urlparse

from flask import current_app

from changes.config import db
from changes.jobs.sync_grouper import (
    _get_admin_emails_from_grouper, _sync_admin_users,
    _get_project_admin_mapping_from_grouper, _sync_project_admin_users,
    sync_grouper,
    GrouperApiError,
)
from changes.models.user import User
from changes.testutils import TestCase


class SyncGrouperAdminTestCase(TestCase):

    @responses.activate
    def test_get_admin_emails_from_grouper_correct(self):
        url = urlparse.urljoin(current_app.config['GROUPER_API_URL'],
                               '/permissions/{}'.format(current_app.config['GROUPER_PERMISSIONS_ADMIN']))
        responses.add(responses.GET, url, json={
            'data': {
                'groups': {
                    'group1': {
                        'users': {
                            'user1@dropbox.com': {'rolename': 'owner'},
                            'user2@dropbox.com': {'rolename': 'member'},
                            'user3@dropbox.com': {'rolename': 'member'},
                        }
                    },
                    'group2': {
                        'users': {
                            'user3@dropbox.com': {'rolename': 'member'},
                            'user4@dropbox.com': {'rolename': 'member'},
                        }
                    }
                }
            }
        })
        admin_usernames = _get_admin_emails_from_grouper()

        assert admin_usernames == set([
            'user1@dropbox.com',
            'user2@dropbox.com',
            'user3@dropbox.com',
            'user4@dropbox.com',
        ])

    @responses.activate
    def test_get_admin_emails_from_grouper_np_owner(self):
        url = urlparse.urljoin(current_app.config['GROUPER_API_URL'],
                               '/permissions/{}'.format(current_app.config['GROUPER_PERMISSIONS_ADMIN']))
        responses.add(responses.GET, url, json={
            'data': {
                'groups': {
                    'group1': {
                        'users': {
                            'user1@dropbox.com': {'rolename': 'np-owner'},
                            'user2@dropbox.com': {'rolename': 'member'},
                            'user3@dropbox.com': {'rolename': 'member'},
                        }
                    },
                    'group2': {
                        'users': {
                            'user3@dropbox.com': {'rolename': 'member'},
                            'user4@dropbox.com': {'rolename': 'member'},
                        }
                    }
                }
            }
        })
        admin_usernames = _get_admin_emails_from_grouper()
        assert admin_usernames == set([
            'user2@dropbox.com',
            'user3@dropbox.com',
            'user4@dropbox.com',
        ])

    @responses.activate
    def test_get_admin_emails_from_grouper_api_error(self):
        url = urlparse.urljoin(current_app.config['GROUPER_API_URL'],
                               '/permissions/{}'.format(current_app.config['GROUPER_PERMISSIONS_ADMIN']))
        responses.add(responses.GET, url, json={
            'errors': [
                {
                    'message': 'This is an error',
                    'code': 500,
                },
                {
                    'message': 'This is another error',
                    'code': 400,
                },
            ]
        })
        with pytest.raises(GrouperApiError) as e:
            _get_admin_emails_from_grouper()
        assert 'This is an error' in '{}'.format(e.value)
        assert 'This is another error' in '{}'.format(e.value)

    def test_sync_admin_users_correct(self):
        admin_user1 = self.create_user(
            email='user1@dropbox.com', is_admin=True)
        admin_user2 = self.create_user(
            email='user2@dropbox.com', is_admin=True)
        admin_user3 = self.create_user(
            email='user3@dropbox.com', is_admin=True)

        user4 = self.create_user(email='user4@dropbox.com', is_admin=False)
        user5 = self.create_user(email='user5@dropbox.com', is_admin=False)

        _sync_admin_users(
            set([u'user2@dropbox.com', u'user3@dropbox.com', u'user5@dropbox.com']))
        db.session.expire_all()

        assert admin_user1.is_admin is False

        assert admin_user2.is_admin is True

        assert admin_user3.is_admin is True

        assert user4.is_admin is False

        assert user5.is_admin is True

    def test_sync_admin_users_new_users(self):
        admin_user1 = self.create_user(
            email='user1@dropbox.com', is_admin=True)
        admin_user3 = self.create_user(
            email='user3@dropbox.com', is_admin=True)

        user4 = self.create_user(email='user4@dropbox.com', is_admin=False)
        user5 = self.create_user(email='user5@dropbox.com', is_admin=False)

        _sync_admin_users(
            set([u'user2@dropbox.com', u'user3@dropbox.com', u'user5@dropbox.com']))
        db.session.expire_all()

        assert admin_user1.is_admin is False

        admin_user2 = User.query.filter(
            User.email == 'user2@dropbox.com').limit(1).first()
        assert admin_user2.is_admin is True

        assert admin_user3.is_admin is True

        assert user4.is_admin is False

        assert user5.is_admin is True


class SyncGrouperProjectAdminTestCase(TestCase):

    def _create_mock_permission(self, permission_name, argument):
        mock_permission = mock.MagicMock()
        mock_permission.permission = permission_name
        mock_permission.argument = argument
        return mock_permission

    @responses.activate
    def test_get_project_admin_mapping_from_grouper_correct(self):
        url = urlparse.urljoin(current_app.config['GROUPER_API_URL'],
                               '/permissions/{}'.format(current_app.config['GROUPER_PERMISSIONS_PROJECT_ADMIN']))
        responses.add(responses.GET, url, json={
            'data': {
                'groups': {
                    'group1': {
                        'users': {
                            'user1@dropbox.com': {'rolename': 'owner'},
                            'user2@dropbox.com': {'rolename': 'member'},
                            'user3@dropbox.com': {'rolename': 'member'},
                        },
                        'permissions': [
                            {
                                'permission': current_app.config['GROUPER_PERMISSIONS_PROJECT_ADMIN'],
                                'argument': 'someproject',
                            },
                            {
                                'permission': current_app.config['GROUPER_PERMISSIONS_PROJECT_ADMIN'],
                                'argument': 'other:*',
                            },
                        ],
                    },
                    'group2': {
                        'users': {
                            'user3@dropbox.com': {'rolename': 'member'},
                            'user4@dropbox.com': {'rolename': 'member'},
                        },
                        'permissions': [
                            {
                                'permission': current_app.config['GROUPER_PERMISSIONS_PROJECT_ADMIN'],
                                'argument': '*otherproject*',
                            },
                        ],
                    }
                }
            }
        })
        mapping = _get_project_admin_mapping_from_grouper()
        assert mapping == {
            'user1@dropbox.com': set(['someproject', 'other:*']),
            'user2@dropbox.com': set(['someproject', 'other:*']),
            'user3@dropbox.com': set(['someproject', 'other:*', '*otherproject*']),
            'user4@dropbox.com': set(['*otherproject*']),
        }

    @responses.activate
    def test_get_project_admin_mapping_from_grouper_np_owner(self):
        url = urlparse.urljoin(current_app.config['GROUPER_API_URL'],
                               '/permissions/{}'.format(current_app.config['GROUPER_PERMISSIONS_PROJECT_ADMIN']))
        responses.add(responses.GET, url, json={
            'data': {
                'groups': {
                    'group1': {
                        'users': {
                            'user1@dropbox.com': {'rolename': 'np-owner'},
                            'user2@dropbox.com': {'rolename': 'member'},
                            'user3@dropbox.com': {'rolename': 'member'},
                        },
                        'permissions': [
                            {
                                'permission': current_app.config['GROUPER_PERMISSIONS_PROJECT_ADMIN'],
                                'argument': 'someproject',
                            },
                            {
                                'permission': current_app.config['GROUPER_PERMISSIONS_PROJECT_ADMIN'],
                                'argument': 'other:*',
                            },
                        ],
                    },
                    'group2': {
                        'users': {
                            'user3@dropbox.com': {'rolename': 'np-owner'},
                            'user4@dropbox.com': {'rolename': 'member'},
                        },
                        'permissions': [
                            {
                                'permission': current_app.config['GROUPER_PERMISSIONS_PROJECT_ADMIN'],
                                'argument': '*otherproject*',
                            },
                        ],
                    }
                }
            }
        })
        mapping = _get_project_admin_mapping_from_grouper()
        assert mapping == {
            'user2@dropbox.com': set(['someproject', 'other:*']),
            'user3@dropbox.com': set(['someproject', 'other:*']),
            'user4@dropbox.com': set(['*otherproject*']),
        }

    @responses.activate
    def test_get_project_admin_mapping_from_grouper_wrong_permission(self):
        url = urlparse.urljoin(current_app.config['GROUPER_API_URL'],
                               '/permissions/{}'.format(current_app.config['GROUPER_PERMISSIONS_PROJECT_ADMIN']))
        responses.add(responses.GET, url, json={
            'data': {
                'groups': {
                    'group1': {
                        'users': {
                            'user1@dropbox.com': {'rolename': 'owner'},
                            'user2@dropbox.com': {'rolename': 'member'},
                            'user3@dropbox.com': {'rolename': 'member'},
                        },
                        'permissions': [
                            {
                                'permission': 'some.other.permission',
                                'argument': 'someproject',
                            },
                            {
                                'permission': current_app.config['GROUPER_PERMISSIONS_PROJECT_ADMIN'],
                                'argument': 'other:*',
                            },
                        ],
                    },
                    'group2': {
                        'users': {
                            'user3@dropbox.com': {'rolename': 'member'},
                            'user4@dropbox.com': {'rolename': 'member'},
                        },
                        'permissions': [
                            {
                                'permission': current_app.config['GROUPER_PERMISSIONS_PROJECT_ADMIN'],
                                'argument': '*otherproject*',
                            },
                        ],
                    }
                }
            }
        })
        mapping = _get_project_admin_mapping_from_grouper()
        assert mapping == {
            'user1@dropbox.com': set(['other:*']),
            'user2@dropbox.com': set(['other:*']),
            'user3@dropbox.com': set(['other:*', '*otherproject*']),
            'user4@dropbox.com': set(['*otherproject*']),
        }

    @responses.activate
    def test_get_project_admin_mapping_from_grouper_empty_pattern(self):
        url = urlparse.urljoin(current_app.config['GROUPER_API_URL'],
                               '/permissions/{}'.format(current_app.config['GROUPER_PERMISSIONS_PROJECT_ADMIN']))
        responses.add(responses.GET, url, json={
            'data': {
                'groups': {
                    'group1': {
                        'users': {
                            'user1@dropbox.com': {'rolename': 'owner'},
                            'user2@dropbox.com': {'rolename': 'member'},
                            'user3@dropbox.com': {'rolename': 'member'},
                        },
                        'permissions': [
                            {
                                'permission': current_app.config['GROUPER_PERMISSIONS_PROJECT_ADMIN'],
                                'argument': '',
                            },
                            {
                                'permission': current_app.config['GROUPER_PERMISSIONS_PROJECT_ADMIN'],
                                'argument': 'other:*',
                            },
                        ],
                    },
                    'group2': {
                        'users': {
                            'user3@dropbox.com': {'rolename': 'member'},
                            'user4@dropbox.com': {'rolename': 'member'},
                        },
                        'permissions': [
                            {
                                'permission': current_app.config['GROUPER_PERMISSIONS_PROJECT_ADMIN'],
                                'argument': '*otherproject*',
                            },
                        ],
                    }
                }
            }
        })
        mapping = _get_project_admin_mapping_from_grouper()
        assert mapping == {
            'user1@dropbox.com': set(['other:*']),
            'user2@dropbox.com': set(['other:*']),
            'user3@dropbox.com': set(['other:*', '*otherproject*']),
            'user4@dropbox.com': set(['*otherproject*']),
        }

    @responses.activate
    def test_get_project_admin_mapping_from_grouper_no_permissions(self):
        url = urlparse.urljoin(current_app.config['GROUPER_API_URL'],
                               '/permissions/{}'.format(current_app.config['GROUPER_PERMISSIONS_PROJECT_ADMIN']))
        responses.add(responses.GET, url, json={
            'data': {
                'groups': {
                    'group1': {
                        'users': {
                            'user1@dropbox.com': {'rolename': 'owner'},
                            'user2@dropbox.com': {'rolename': 'member'},
                            'user3@dropbox.com': {'rolename': 'member'},
                        },
                        'permissions': [
                            {
                                'permission': current_app.config['GROUPER_PERMISSIONS_PROJECT_ADMIN'],
                                'argument': 'someproject',
                            },
                            {
                                'permission': current_app.config['GROUPER_PERMISSIONS_PROJECT_ADMIN'],
                                'argument': 'other:*',
                            },
                        ],
                    },
                    'group2': {
                        'users': {
                            'user3@dropbox.com': {'rolename': 'member'},
                            'user4@dropbox.com': {'rolename': 'member'},
                        },
                        'permissions': [],
                    }
                }
            }
        })
        mapping = _get_project_admin_mapping_from_grouper()
        assert mapping == {
            'user1@dropbox.com': set(['someproject', 'other:*']),
            'user2@dropbox.com': set(['someproject', 'other:*']),
            'user3@dropbox.com': set(['someproject', 'other:*']),
        }

    @responses.activate
    def test_get_project_admin_mapping_from_grouper_api_error_missing(self):
        url = urlparse.urljoin(current_app.config['GROUPER_API_URL'],
                               '/permissions/{}'.format(current_app.config['GROUPER_PERMISSIONS_PROJECT_ADMIN']))
        responses.add(responses.GET, url, json={
            'errors': [
                {
                    'message': 'This is an error',
                    'code': 404,
                },
            ]
        })
        mapping = _get_project_admin_mapping_from_grouper()
        assert mapping == dict()

    @responses.activate
    def test_get_project_admin_mapping_from_grouper_api_error_other(self):
        url = urlparse.urljoin(current_app.config['GROUPER_API_URL'],
                               '/permissions/{}'.format(current_app.config['GROUPER_PERMISSIONS_PROJECT_ADMIN']))
        responses.add(responses.GET, url, json={
            'errors': [
                {
                    'message': 'This is an error',
                    'code': 404,
                },
                {
                    'message': 'This is another error',
                    'code': 500
                },
            ]
        })
        with pytest.raises(GrouperApiError) as e:
            _get_project_admin_mapping_from_grouper()
        assert 'This is an error' in '{}'.format(e.value)
        assert 'This is another error' in '{}'.format(e.value)

    def test_sync_project_admin_users_correct(self):
        user1 = self.create_user(
            email='user1@dropbox.com', project_permissions=['other:*', 'projectB'])
        user2 = self.create_user(
            email='user2@dropbox.com', project_permissions=['other:*'])
        user3 = self.create_user(
            email='user3@dropbox.com', project_permissions=['projectB'])
        user4 = self.create_user(
            email='user4@dropbox.com')
        assert user4.project_permissions is None
        _sync_project_admin_users({
            'user2@dropbox.com': set(['other:*', 'projectB']),
            'user3@dropbox.com': set(['other:*', '*project*']),
            'user4@dropbox.com': set(['projectB']),
        })
        db.session.expire_all()
        assert user1.project_permissions is None
        assert set(user2.project_permissions) == set(['other:*', 'projectB'])
        assert set(user3.project_permissions) == set(['other:*', '*project*'])
        assert set(user4.project_permissions) == set(['projectB'])

    def test_sync_project_admin_users_new_users(self):
        user1 = self.create_user(
            email='user1@dropbox.com', project_permissions=['other:*', 'projectB'])
        user3 = self.create_user(
            email='user3@dropbox.com', project_permissions=['projectB'])
        user4 = self.create_user(
            email='user4@dropbox.com')
        assert user4.project_permissions is None
        _sync_project_admin_users({
            'user2@dropbox.com': set(['other:*', 'projectB']),
            'user3@dropbox.com': set(['other:*', '*project*']),
            'user4@dropbox.com': set(['projectB']),
        })
        db.session.expire_all()
        assert user1.project_permissions is None
        user2 = User.query.filter(
            User.email == 'user2@dropbox.com').limit(1).first()
        assert set(user2.project_permissions) == set(['other:*', 'projectB'])
        assert set(user3.project_permissions) == set(['other:*', '*project*'])
        assert set(user4.project_permissions) == set(['projectB'])


class SyncGrouperTestCase(TestCase):

    def test_sync_grouper_stats_succeeded(self):
        with mock.patch('changes.jobs.sync_grouper._get_admin_emails_from_grouper'):
            with mock.patch('changes.jobs.sync_grouper._sync_admin_users'):
                with mock.patch('changes.jobs.sync_grouper._get_project_admin_mapping_from_grouper'):
                    with mock.patch('changes.jobs.sync_grouper._sync_project_admin_users'):
                        with mock.patch('changes.jobs.sync_grouper.statsreporter') as mock_statsreporter:
                            sync_grouper()
        mock_statsreporter.stats().set_gauge.assert_called_once_with('grouper_sync_error', 0)

    def test_sync_grouper_stats_failure(self):
        with mock.patch('changes.jobs.sync_grouper._get_admin_emails_from_grouper') as mock_call:
            with mock.patch('changes.jobs.sync_grouper.statsreporter') as mock_statsreporter:
                mock_call.side_effect = Exception
                with pytest.raises(Exception):
                    sync_grouper()
        mock_statsreporter.stats().set_gauge.assert_called_once_with('grouper_sync_error', 1)
