import changes
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

        dev_js_should_hit_host = current_app.config['DEV_JS_SHOULD_HIT_HOST']

        # use new react code
        if self.use_v2:
            return render_template('webapp.html', **{
                'SENTRY_PUBLIC_DSN': dsn,
                'VERSION': changes.get_version(),
                'DEV_JS_SHOULD_HIT_HOST': dev_js_should_hit_host
            })

        return render_template('index.html', **{
            'SENTRY_PUBLIC_DSN': dsn,
            'VERSION': changes.get_version(),
            'DEV_JS_SHOULD_HIT_HOST': dev_js_should_hit_host
        })
