import mock

from base64 import urlsafe_b64decode
from datetime import datetime
from flask import current_app
from oauth2client import GOOGLE_REVOKE_URI, GOOGLE_TOKEN_URI
from oauth2client.client import OAuth2Credentials
from urlparse import urlparse, parse_qs

from changes.models.user import User
from changes.testutils import TestCase


class LoginViewTest(TestCase):

    def test_simple(self):
        resp = self.client.get('/auth/login/')
        assert resp.status_code == 302
        parsed_location = urlparse(resp.headers['Location'])
        assert parsed_location.scheme == 'https'
        assert parsed_location.netloc == 'accounts.google.com'
        assert parsed_location.path == '/o/oauth2/auth'
        assert parse_qs(parsed_location.query) == {
            'scope': ['email'],
            'redirect_uri': ['http://localhost/auth/complete/'],
            'response_type': ['code'],
            'client_id': ['aaaaaaaaaaaa'],
            'access_type': ['offline'],
            'approval_prompt': ['force']
        }

    def test_with_state(self):
        resp = self.client.get('/auth/login/?orig_url=nowhere')
        parsed_location = urlparse(resp.headers['Location'])
        query_params = parse_qs(parsed_location.query)
        assert "state" in query_params
        assert urlsafe_b64decode(query_params['state'][0]) == 'nowhere'


class AuthorizedViewTest(TestCase):

    @mock.patch('changes.web.auth.OAuth2WebServerFlow.step2_exchange')
    def test_simple(self, step2_exchange):
        access_token = 'b' * 40
        refresh_token = 'c' * 40

        step2_exchange.return_value = OAuth2Credentials(
            access_token, current_app.config['GOOGLE_CLIENT_ID'],
            current_app.config['GOOGLE_CLIENT_SECRET'],
            refresh_token,
            datetime(2013, 9, 19, 22, 15, 22),
            GOOGLE_TOKEN_URI,
            'foo/1.0',
            revoke_uri=GOOGLE_REVOKE_URI,
            id_token={
                'hd': 'example.com',
                'email': 'foo@example.com',
            },
        )

        resp = self.client.get('/auth/complete/?code=abc')

        step2_exchange.assert_called_once_with('abc')

        assert resp.status_code == 302
        assert resp.headers['Location'] == 'http://localhost/?finished_login=success'

        user = User.query.filter(
            User.email == 'foo@example.com',
        ).first()

        assert user


class LogoutViewTest(TestCase):

    def test_simple(self):
        resp = self.client.get('/auth/logout/')
        assert resp.status_code == 302
        assert resp.headers['Location'] == 'http://localhost/'
