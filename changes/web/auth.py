import json

from base64 import urlsafe_b64decode
from flask import current_app, redirect, request, session, url_for
from flask.views import MethodView
from requests_oauthlib import OAuth2Session

from changes.db.utils import get_or_create
from changes.models import User


AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URL = "https://accounts.google.com/o/oauth2/token"
SCOPE = [
    'https://www.googleapis.com/auth/userinfo.email',
]


def get_auth_session(redirect_uri=None):
    # XXX(dcramer): we have to generate this each request because oauth2client
    # doesn't want you to set redirect_uri as part of the request, which causes
    # a lot of runtime issues.
    return OAuth2Session(
        client_id=current_app.config['GOOGLE_CLIENT_ID'],
        scope=SCOPE,
        redirect_uri=redirect_uri,
        # user_agent='changes/{0} (python {1})'.format(
        #     changes.VERSION,
        #     sys.version,
        # )
    )


def decode_id_token(id_token):
    segments = id_token.split('.')

    if (len(segments) != 3):
        raise ValueError('Wrong number of segments in token: %s' % id_token)

    b64string = segments[1]
    b64string = b64string.encode('ascii')
    padded = b64string + b'=' * (4 - len(b64string) % 4)
    padded = urlsafe_b64decode(padded)
    return json.loads(padded.decode('utf-8'))


class LoginView(MethodView):
    def __init__(self, authorized_url):
        self.authorized_url = authorized_url
        super(LoginView, self).__init__()

    def get(self):
        redirect_uri = url_for(self.authorized_url, _external=True)
        oauth = get_auth_session(redirect_uri=redirect_uri)
        auth_uri, state = oauth.authorization_url(
            AUTHORIZATION_URL, access_type="offline")
        return redirect(auth_uri)


class AuthorizedView(MethodView):
    def __init__(self, complete_url, authorized_url):
        self.complete_url = complete_url
        self.authorized_url = authorized_url
        super(AuthorizedView, self).__init__()

    def get(self):
        redirect_uri = url_for(self.authorized_url, _external=True)
        oauth = get_auth_session(redirect_uri=redirect_uri)
        token = oauth.fetch_token(
            TOKEN_URL,
            authorization_response=request.url,
            client_secret=current_app.config['GOOGLE_CLIENT_SECRET'])

        id_token = decode_id_token(token['id_token'])
        if current_app.config['GOOGLE_DOMAIN']:
            # TODO(dcramer): confirm this is actually what this value means
            if id_token.get('hd') != current_app.config['GOOGLE_DOMAIN']:
                # TODO(dcramer): this should show some kind of error
                return redirect(url_for(self.complete_url))

        user, _ = get_or_create(User, where={
            'email': id_token['email'],
        })

        session['uid'] = user.id.hex
        session['access_token'] = token['access_token']
        session['email'] = id_token['email']

        return redirect(url_for(self.complete_url))


class LogoutView(MethodView):
    def __init__(self, complete_url):
        self.complete_url = complete_url
        super(LogoutView, self).__init__()

    def get(self):
        session.pop('uid', None)
        session.pop('access_token', None)
        session.pop('email', None)
        return redirect(url_for(self.complete_url))
