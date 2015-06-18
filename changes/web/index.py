import changes
import os
import urlparse

from changes.config import statsreporter
from flask import render_template, current_app
from flask.views import MethodView


class IndexView(MethodView):
    def __init__(self, use_v2=False):
        self.use_v2 = use_v2
        super(MethodView, self).__init__()

    def get(self, path=''):
        statsreporter.stats().incr('homepage_view')
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

        # variables to ship down to the webapp
        webapp_use_another_host = current_app.config['WEBAPP_USE_ANOTHER_HOST']
        # note that we're only shipping down the filename!
        webapp_customized_content_filename = None
        if current_app.config['WEBAPP_CUSTOMIZED_CONTENT_FILE']:
            webapp_customized_content_filename = os.path.basename(
                current_app.config['WEBAPP_CUSTOMIZED_CONTENT_FILE'])

        # use new react code
        if self.use_v2:
            return render_template('webapp.html', **{
                'SENTRY_PUBLIC_DSN': dsn,
                'VERSION': changes.get_version(),
                'WEBAPP_USE_ANOTHER_HOST': webapp_use_another_host,
                'WEBAPP_CUSTOMIZED_CONTENT_FILENAME': webapp_customized_content_filename
            })

        return render_template('index.html', **{
            'SENTRY_PUBLIC_DSN': dsn,
            'VERSION': changes.get_version(),
            'WEBAPP_USE_ANOTHER_HOST': webapp_use_another_host
        })
