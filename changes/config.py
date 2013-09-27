import flask
import os
import os.path

from flask.ext.sqlalchemy import SQLAlchemy
from flask.helpers import send_from_directory
from flask_redis import Redis

from changes.ext.queue import Queue

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

db = SQLAlchemy(session_options={
    'autoflush': True,
})

queue = Queue()

redis = Redis()


class ChangesApp(flask.Flask):
    def __init__(self, *args, **kwargs):
        self.partials_url_path = kwargs.pop('partials_url_path', '/partials')
        self.partials_folder = kwargs.pop('partials_folder', None)

        super(ChangesApp, self).__init__(*args, **kwargs)

        if self.partials_folder is not None:
            self.add_url_rule(self.partials_url_path + '/<path:filename>',
                              endpoint='partials',
                              view_func=self.send_partial_file)

    def send_partial_file(self, filename):
        if self.partials_folder is None:
            raise RuntimeError('No partials folder for this object')

        cache_timeout = self.get_send_file_max_age(filename)
        return send_from_directory(self.partials_folder, filename,
                                   cache_timeout=cache_timeout)


def create_app(**config):
    app = ChangesApp(__name__,
                     static_folder=os.path.join(PROJECT_ROOT, 'static'),
                     template_folder=os.path.join(PROJECT_ROOT, 'templates'),
                     partials_folder=os.path.join(PROJECT_ROOT, 'partials'))
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://localhost/changes'
    app.config['REDIS_URL'] = 'redis://localhost'
    app.config['RQ_DEFAULT_RESULT_TTL'] = 0
    # app.config['SQLALCHEMY_ECHO'] = True
    app.config['DEBUG'] = True
    app.config['JENKINS_URL'] = 'http://54.213.59.142'
    # app.config['UPLOAD_FOLDER'] = PROJECT_ROOT + '/uploads'
    # if not path.isdir(app.config['UPLOAD_FOLDER']):
    #     mkdir(app.config['UPLOAD_FOLDER'])
    # app.config['AWS_ACCESS_KEY'] = os.environ['AWS_ACCESS_KEY']
    # app.config['AWS_SECRET_KEY'] = os.environ['AWS_SECRET_KEY']
    app.config['HTTP_PORT'] = 5000
    app.config['KOALITY_URL'] = 'https://build.itc.dropbox.com'
    app.config['KOALITY_API_KEY'] = 'he8i7mxdzrocn6rg9qv852occkvpih9b'
    app.config.update(config)

    db.init_app(app)
    queue.init_app(app)
    redis.init_app(app)

    # TODO: these can be moved to wsgi app entrypoints
    configure_api_routes(app)
    configure_web_routes(app)

    configure_jobs(app)

    return app


def configure_api_routes(app):
    from changes.api.build_index import BuildIndexAPIView
    from changes.api.build_details import BuildDetailsAPIView
    from changes.api.stream import StreamAPIView, TestStreamAPIView

    app.add_url_rule(
        '/api/0/stream/', view_func=StreamAPIView.as_view('api-stream'))
    app.add_url_rule(
        '/api/0/stream/test/', view_func=TestStreamAPIView.as_view('api-stream-test'))
    app.add_url_rule(
        '/api/0/builds/', view_func=BuildIndexAPIView.as_view('api-builds'))
    app.add_url_rule(
        '/api/0/builds/<build_id>/', view_func=BuildDetailsAPIView.as_view('api-build-details'))


def configure_web_routes(app):
    from changes.web.index import IndexView

    app.add_url_rule(
        r'/', view_func=IndexView.as_view('index'))


def configure_jobs(app):
    import changes.jobs.sync_build  # NOQA
