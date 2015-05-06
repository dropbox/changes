from __future__ import absolute_import

import json
import unittest

from exam import Exam, fixture
from flask import current_app as app

from changes.config import db, mail
from changes.models import User
from changes.testutils.fixtures import Fixtures


class AuthMixin(object):
    @fixture
    def default_user(self):
        user = User(
            email='foo@example.com',
        )
        db.session.add(user)
        db.session.commit()

        return user

    @fixture
    def default_admin(self):
        user = User(
            email='bar@example.com',
            is_admin=True,
        )
        db.session.add(user)
        db.session.commit()

        return user

    def login(self, user):
        with self.client.session_transaction() as session:
            session['uid'] = user.id.hex
            session['email'] = user.email
        return user

    def login_default(self):
        return self.login(self.default_user)

    def login_default_admin(self):
        return self.login(self.default_admin)


class TestCase(Exam, unittest.TestCase, Fixtures, AuthMixin):
    def setUp(self):
        # mock out mail
        mail_context = mail.record_messages()
        self.outbox = mail_context.__enter__()
        self.addCleanup(lambda: mail_context.__exit__(None, None, None))

        self.client = app.test_client()

        super(TestCase, self).setUp()

    def unserialize(self, response):
        assert response.headers['Content-Type'] == 'application/json'
        return json.loads(response.data)


class BackendTestCase(TestCase):
    backend_cls = None
    backend_options = {}

    def get_backend(self):
        return self.backend_cls(
            app=app, **self.backend_options
        )


class APITestCase(TestCase):
    pass
