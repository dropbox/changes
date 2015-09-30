import base64
import changes
import sys
import urllib
import urlparse
import time
import requests

from cryptography.fernet import Fernet
from flask import current_app, redirect, request, session, url_for
from flask.views import MethodView
from oauth2client.client import OAuth2WebServerFlow

from changes.config import db
from changes.db.utils import get_or_create
from changes.models import User

GOOGLE_AUTH_URI = 'https://accounts.google.com/o/oauth2/auth'
GOOGLE_REVOKE_URI = 'https://accounts.google.com/o/oauth2/revoke'
GOOGLE_TOKEN_URI = 'https://accounts.google.com/o/oauth2/token'

MAX_AGE = 2419200  # 28 days


def get_auth_flow(redirect_uri=None, state=""):
    # XXX(dcramer): we have to generate this each request because oauth2client
    # doesn't want you to set redirect_uri as part of the request, which causes
    # a lot of runtime issues.
    auth_uri = GOOGLE_AUTH_URI
    if current_app.config['GOOGLE_DOMAIN']:
        auth_uri = auth_uri + '?hd=' + current_app.config['GOOGLE_DOMAIN']

    return OAuth2WebServerFlow(
        client_id=current_app.config['GOOGLE_CLIENT_ID'],
        client_secret=current_app.config['GOOGLE_CLIENT_SECRET'],
        scope='email',
        redirect_uri=redirect_uri,
        user_agent='changes/{0} (python {1})'.format(
            changes.VERSION,
            # Newer versions of Python stdlib disallow newlines in header values.
            # See http://bugs.python.org/issue22928
            sys.version.replace('\n', ' -- '),
        ),
        auth_uri=auth_uri,
        token_uri=GOOGLE_TOKEN_URI,
        revoke_uri=GOOGLE_REVOKE_URI,
        state=state,
        approval_prompt='force',
        access_type='offline'
        )


def auth_with_refresh_token(cookies):
    """
    Requests authorization using the refresh token available,
    without prompting the user.

    Parameters:
        cookies: the available request cookies

    Returns:
        The entire response from Google.
    """

    refresh_token = Fernet(current_app.config['COOKIE_ENCRYPTION_KEY']).decrypt(str(cookies['refresh_token']))

    values = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'client_id': current_app.config['GOOGLE_CLIENT_ID'],
        'client_secret': current_app.config['GOOGLE_CLIENT_SECRET']
    }
    headers = {'content-type': 'application/x-www-form-urlencoded'}
    refresh_request = requests.post(GOOGLE_TOKEN_URI, data=values, headers=headers)
    resp = refresh_request.json()

    return resp


def get_orig_url_redirect(state):
    """
    Parameters:
        state: Encoded url that forwards to the page the user
        originally tried to access.

    Returns:
        A redirect object which forwards the user to the
        page they originally tried to access before they
        were sent to authorize.
    """

    if state:
        originating_url = base64.urlsafe_b64decode(state.encode('utf-8'))
    else:
        originating_url = url_for('index')

    # add a query parameter. It shouldn't be this cumbersome...
    url_parts = list(urlparse.urlparse(originating_url))
    query = dict(urlparse.parse_qsl(url_parts[4]))
    query['finished_login'] = 'success'
    url_parts[4] = urllib.urlencode(query)

    return redirect(urlparse.urlunparse(url_parts))


def set_session_state(access_token=None, email=None):
    """
    Sets local session state. If user does not exist in
    db, then we create a new user as well.

    Parameters:
        access_token: The current Google auth access_token, when available.
        email: The user's email address, when available.

    Returns:
        None
    """

    user, _ = get_or_create(User, where={
        'email': email,
    })

    if current_app.config['DEBUG']:
        user.is_admin = True
        db.session.add(user)

    session['uid'] = user.id.hex
    session['access_token'] = access_token
    session['email'] = email


class LoginView(MethodView):
    def __init__(self, authorized_url):
        self.authorized_url = authorized_url
        super(LoginView, self).__init__()

    def get(self):
        state = ""
        if 'orig_url' in request.args:
            # we'll later redirect the user back the page they were on after
            # logging in
            state = base64.urlsafe_b64encode(request.args['orig_url'].encode('utf-8'))

        # if refresh token available, log in without prompt
        if 'refresh_token' in request.cookies and 'refresh_email' in request.cookies:
            resp = auth_with_refresh_token(request.cookies)
            email = Fernet(current_app.config['COOKIE_ENCRYPTION_KEY']).decrypt(str(request.cookies['refresh_email']))

            set_session_state(access_token=resp['access_token'],
                email=email)

            return get_orig_url_redirect(state)

        redirect_uri = url_for(self.authorized_url, _external=True)

        flow = get_auth_flow(redirect_uri=redirect_uri, state=state)
        auth_uri = flow.step1_get_authorize_url()

        return redirect(auth_uri)


class AuthorizedView(MethodView):
    def __init__(self, complete_url, authorized_url):
        self.complete_url = complete_url
        self.authorized_url = authorized_url
        super(AuthorizedView, self).__init__()

    def get(self):
        redirect_uri = url_for(self.authorized_url, _external=True)
        state = request.args.get("state", "")
        flow = get_auth_flow(redirect_uri=redirect_uri, state=state)
        resp = flow.step2_exchange(request.args['code'])

        if current_app.config['GOOGLE_DOMAIN']:
            # TODO(dcramer): confirm this is actually what this value means
            if resp.id_token.get('hd') != current_app.config['GOOGLE_DOMAIN']:
                # TODO(dcramer): this should show some kind of error
                return redirect(url_for(self.complete_url, {'finished_login': 'error'}))

        set_session_state(access_token=resp.access_token, email=resp.id_token['email'])

        # if the user came from a specific page, modify response object
        # to reflect that
        response_redirect = (get_orig_url_redirect(state) if state
            else redirect(url_for(self.complete_url, finished_login='success')))

        response = current_app.make_response(response_redirect)

        # create and save cookies
        # need to set expires /just in case/ anyone uses IE :(
        encrypted_token = Fernet(current_app.config['COOKIE_ENCRYPTION_KEY']).encrypt(str(resp.refresh_token))
        response.set_cookie('refresh_token', value=encrypted_token,
        max_age=MAX_AGE, expires=int(time.time() + MAX_AGE))

        encrypted_email = Fernet(current_app.config['COOKIE_ENCRYPTION_KEY']).encrypt(str(session['email']))
        response.set_cookie('refresh_email', value=encrypted_email,
        max_age=MAX_AGE, expires=int(time.time() + MAX_AGE))

        return response


class LogoutView(MethodView):
    def __init__(self, complete_url):
        self.complete_url = complete_url
        super(LogoutView, self).__init__()

    def get(self):
        session.pop('uid', None)
        session.pop('access_token', None)
        session.pop('email', None)

        response_redirect = redirect(url_for(self.complete_url))

        # if the url contains ?return, go back to the referrer page
        if 'return' in request.args and request.referrer:
            is_same_host = (urlparse.urlparse(request.referrer).netloc ==
                urlparse.urlparse(request.host_url).netloc)
            if is_same_host:
                response_redirect = redirect(request.referrer)

        # remove refresh token and login email
        response = current_app.make_response(response_redirect)
        response.delete_cookie('refresh_token')
        response.delete_cookie('refresh_email')

        return response
