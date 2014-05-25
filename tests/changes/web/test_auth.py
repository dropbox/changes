import responses

from urllib.parse import parse_qsl

from changes.testutils import TestCase


class LoginViewTest(TestCase):
    @responses.activate
    def test_simple(self):
        resp = self.client.get('/auth/login/', base_url='https://localhost')
        assert resp.status_code == 302
        location = resp.headers['Location']
        assert location.startswith('https://accounts.google.com/o/oauth2/auth?')
        query = location.rsplit('?', 1)[1]
        components = parse_qsl(query)
        expected = [
            ('access_type', 'offline'),
            ('client_id', 'aaaaaaaaaaaa'),
            ('redirect_uri', 'https://localhost/auth/complete/'),
            ('response_type', 'code'),
            ('scope', 'https://www.googleapis.com/auth/userinfo.email'),
        ]
        for item in expected:
            assert item in components


# TODO(dcramer):
# class AuthorizedViewTest(TestCase):
#     @responses.activate
#     @patch('changes.web.auth.decode_id_token')
#     def test_simple(self, mock_decode_id_token):
#         mock_decode_id_token.return_value = {}

#         responses.add(responses.POST, 'https://accounts.google.com/o/oauth2/token',
#             status=302, adding_headers={
#                 'Location': 'https://localhost:5000/auth/complete/?state=THESTATE&code=THECODE'
#             })

#         access_token = 'b' * 40
#         refresh_token = 'c' * 40

#         resp = self.client.get('/auth/complete/?code=abc', base_url='https://localhost')

#         assert resp.status_code == 302
#         assert resp.headers['Location'] == 'https://localhost/'

#         user = User.query.filter(
#             User.email == 'foo@example.com',
#         ).first()

#         assert user


class LogoutViewTest(TestCase):
    @responses.activate
    def test_simple(self):
        resp = self.client.get('/auth/logout/', base_url='https://localhost')
        assert resp.status_code == 302
        assert resp.headers['Location'] == 'https://localhost/'
