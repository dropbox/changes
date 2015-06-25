import base64
import changes
import sys
import urllib
import urlparse

from flask import current_app, redirect, request, session, url_for
from flask.views import MethodView
from oauth2client.client import OAuth2WebServerFlow

from changes.config import db
from changes.db.utils import get_or_create
from changes.models import User

GOOGLE_AUTH_URI = 'https://accounts.google.com/o/oauth2/auth'
GOOGLE_REVOKE_URI = 'https://accounts.google.com/o/oauth2/revoke'
GOOGLE_TOKEN_URI = 'https://accounts.google.com/o/oauth2/token'


def get_auth_flow(redirect_uri=None):
    # XXX(dcramer): we have to generate this each request because oauth2client
    # doesn't want you to set redirect_uri as part of the request, which causes
    # a lot of runtime issues.
    # Addendum (mkedia): An even more fun twist is that the auth uri is different
    # for step 1 and 2: in step 1, we pass a state parameter using a query parameter,
    # but in step 2 we no longer know what that parameter is...
    auth_uri = GOOGLE_AUTH_URI
    if current_app.config['GOOGLE_DOMAIN']:
        auth_uri = auth_uri + '?hd=' + current_app.config['GOOGLE_DOMAIN']

    state = ""
    if 'orig_url' in request.args:
        # we'll later redirect the user back the page they were on after
        # logging in
        state = base64.urlsafe_b64encode(request.args['orig_url'])

    return OAuth2WebServerFlow(
        client_id=current_app.config['GOOGLE_CLIENT_ID'],
        client_secret=current_app.config['GOOGLE_CLIENT_SECRET'],
        scope='https://www.googleapis.com/auth/userinfo.email',
        redirect_uri=redirect_uri,
        user_agent='changes/{0} (python {1})'.format(
            changes.VERSION,
            sys.version,
        ),
        auth_uri=auth_uri,
        token_uri=GOOGLE_TOKEN_URI,
        revoke_uri=GOOGLE_REVOKE_URI,
        state=state
    )


class LoginView(MethodView):
    def __init__(self, authorized_url):
        self.authorized_url = authorized_url
        super(LoginView, self).__init__()

    def get(self):
        redirect_uri = url_for(self.authorized_url, _external=True)
        flow = get_auth_flow(redirect_uri=redirect_uri)
        auth_uri = flow.step1_get_authorize_url()
        return redirect(auth_uri)


class AuthorizedView(MethodView):
    def __init__(self, complete_url, authorized_url):
        self.complete_url = complete_url
        self.authorized_url = authorized_url
        super(AuthorizedView, self).__init__()

    def get(self):
        redirect_uri = url_for(self.authorized_url, _external=True)
        flow = get_auth_flow(redirect_uri=redirect_uri)
        resp = flow.step2_exchange(request.args['code'])

        if current_app.config['GOOGLE_DOMAIN']:
            # TODO(dcramer): confirm this is actually what this value means
            if resp.id_token.get('hd') != current_app.config['GOOGLE_DOMAIN']:
                # TODO(dcramer): this should show some kind of error
                return redirect(url_for(self.complete_url, {'finished_login': 'error'}))

        user, _ = get_or_create(User, where={
            'email': resp.id_token['email'],
        })

        if current_app.config['DEBUG']:
            user.is_admin = True
            db.session.add(user)

        session['uid'] = user.id.hex
        session['access_token'] = resp.access_token
        session['email'] = resp.id_token['email']

        if 'state' in request.args:
            originating_url = base64.urlsafe_b64decode(request.args['state'])
            # add a query parameter. It shouldn't be this cumbersome...
            url_parts = list(urlparse.urlparse(originating_url))
            query = dict(urlparse.parse_qsl(url_parts[4]))
            query['finished_login'] = 'success'
            url_parts[4] = urllib.urlencode(query)

            return redirect(urlparse.urlunparse(url_parts))

        return redirect(url_for(self.complete_url, finished_login='success'))


class LogoutView(MethodView):
    def __init__(self, complete_url):
        self.complete_url = complete_url
        super(LogoutView, self).__init__()

    def get(self):
        session.pop('uid', None)
        session.pop('access_token', None)
        session.pop('email', None)
        # if the url contains ?return, go back to the referrer page
        if 'return' in request.args and request.referrer:
            is_same_host = (urlparse.urlparse(request.referrer).netloc ==
                urlparse.urlparse(request.host_url).netloc)
            if is_same_host:
                return redirect(request.referrer)

        return redirect(url_for(self.complete_url))
