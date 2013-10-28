from flask import current_app, redirect, request, session, url_for

from changes.api.base import MethodView
from changes.config import google_auth


class LoginView(MethodView):
    def __init__(self, authorized_url):
        self.authorized_url = authorized_url
        super(LoginView, self).__init__()

    def get(self):
        callback = url_for(self.authorized_url, _external=True)
        auth_uri = google_auth.step1_get_authorize_url(callback)
        return redirect(auth_uri)


class AuthorizedView(MethodView):
    def __init__(self, complete_url):
        self.complete_url = complete_url
        super(AuthorizedView, self).__init__()

    def get(self):
        resp = google_auth.step2_exchange(request.args['code'])

        if current_app.config['GOOGLE_DOMAIN']:
            # TODO(dcramer): confirm this is actually what this value means
            if resp.id_token.get('hd') != current_app.config['GOOGLE_DOMAIN']:
                # TODO(dcramer): this should show some kind of error
                return redirect(self.complete_url)

        session['access_token'] = resp.access_token
        session['email'] = resp.id_token['email']

        return redirect(self.complete_url)


class LogoutView(MethodView):
    def __init__(self, complete_url):
        self.complete_url = complete_url
        super(LogoutView, self).__init__()

    def get(self):
        session.pop('access_token', None)
        session.pop('email', None)
        return redirect(self.complete_url)
