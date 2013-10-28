from oauth2client.client import OAuth2WebServerFlow

from .container import Container


def make_google_auth(app, options):
    return OAuth2WebServerFlow(
        client_id=app.config['GOOGLE_CLIENT_ID'],
        client_secret=app.config['GOOGLE_CLIENT_SECRET'],
        scope='https://www.googleapis.com/auth/userinfo.email',
    )

GoogleAuth = lambda **o: Container(make_google_auth, o, name='google-auth')
