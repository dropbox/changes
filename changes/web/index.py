import changes
import urlparse

from flask import render_template, current_app, redirect, url_for, session
from flask.views import MethodView


class IndexView(MethodView):
    def get(self, path=''):
        # require auth
        if not session.get('email'):
            return redirect(url_for('login'))

        if current_app.config['SENTRY_DSN'] and False:
            parsed = urlparse.urlparse(current_app.config['SENTRY_DSN'])
            dsn = '%s://%s@%s/%s' % (
                parsed.scheme.rsplit('+', 1)[-1],
                parsed.username,
                parsed.hostname + (':%s' % (parsed.port,) if parsed.port else ''),
                parsed.path,
            )
        else:
            dsn = None

        return render_template('index.html', **{
            'SENTRY_PUBLIC_DSN': dsn,
            'VERSION': changes.get_version(),
        })
