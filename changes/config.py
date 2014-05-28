import changes
import logging
import flask
import os
import os.path
import warnings

from celery.signals import task_postrun
from datetime import timedelta
from flask import request, session
from flask.ext.sqlalchemy import SQLAlchemy
from flask_debugtoolbar import DebugToolbarExtension
from flask_mail import Mail
from kombu import Exchange, Queue
from raven.contrib.flask import Sentry
from urlparse import urlparse
from werkzeug.contrib.fixers import ProxyFix

from changes.constants import PROJECT_ROOT
from changes.api.controller import APIController
from changes.ext.celery import Celery
from changes.ext.redis import Redis
from changes.url_converters.uuid import UUIDConverter

# because foo.in_([]) ever executing is a bad idea
from sqlalchemy.exc import SAWarning
warnings.simplefilter('error', SAWarning)


class ChangesDebugToolbarExtension(DebugToolbarExtension):
    def _show_toolbar(self):
        if '__trace__' in request.args:
            return True
        return super(ChangesDebugToolbarExtension, self)._show_toolbar()

    def process_response(self, response):
        real_request = request._get_current_object()

        # If the http response code is 200 then we process to add the
        # toolbar to the returned html response.
        if '__trace__' in real_request.args:
            for panel in self.debug_toolbars[real_request].panels:
                panel.process_response(real_request, response)

            if response.is_sequence:
                toolbar_html = self.debug_toolbars[real_request].render_toolbar()
                response.headers['content-type'] = 'text/html'
                response.response = [toolbar_html]
                response.content_length = len(toolbar_html)

        return response

db = SQLAlchemy(session_options={})
api = APIController(prefix='/api/0')
mail = Mail()
queue = Celery()
redis = Redis()
sentry = Sentry(logging=True, level=logging.ERROR)


def create_app(_read_config=True, **config):
    app = flask.Flask(__name__,
                      static_folder=None,
                      template_folder=os.path.join(PROJECT_ROOT, 'templates'))

    app.wsgi_app = ProxyFix(app.wsgi_app)
    # app.wsgi_app = TracerMiddleware(app.wsgi_app, app)

    # This key is insecure and you should override it on the server
    app.config['SECRET_KEY'] = 't\xad\xe7\xff%\xd2.\xfe\x03\x02=\xec\xaf\\2+\xb8=\xf7\x8a\x9aLD\xb1'

    app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql:///changes'
    app.config['SQLALCHEMY_POOL_SIZE'] = 60
    app.config['SQLALCHEMY_MAX_OVERFLOW'] = 20
    # required for flask-debugtoolbar
    app.config['SQLALCHEMY_RECORD_QUERIES'] = True

    app.config['REDIS_URL'] = 'redis://localhost/0'
    app.config['DEBUG'] = True
    app.config['HTTP_PORT'] = 5000
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

    app.config['API_TRACEBACKS'] = True

    app.config['CELERY_ACCEPT_CONTENT'] = ['changes_json']
    app.config['CELERY_ACKS_LATE'] = True
    app.config['CELERY_BROKER_URL'] = 'redis://localhost/0'
    app.config['CELERY_DEFAULT_QUEUE'] = "default"
    app.config['CELERY_DEFAULT_EXCHANGE'] = "default"
    app.config['CELERY_DEFAULT_EXCHANGE_TYPE'] = "direct"
    app.config['CELERY_DEFAULT_ROUTING_KEY'] = "default"
    app.config['CELERY_DISABLE_RATE_LIMITS'] = True
    app.config['CELERY_IGNORE_RESULT'] = True
    app.config['CELERY_RESULT_BACKEND'] = None
    app.config['CELERY_RESULT_SERIALIZER'] = 'changes_json'
    app.config['CELERY_SEND_EVENTS'] = False
    app.config['CELERY_TASK_RESULT_EXPIRES'] = 1
    app.config['CELERY_TASK_SERIALIZER'] = 'changes_json'
    app.config['CELERYD_PREFETCH_MULTIPLIER'] = 1
    app.config['CELERYD_MAX_TASKS_PER_CHILD'] = 10000

    app.config['CELERY_QUEUES'] = (
        Queue('job.sync', routing_key='job.sync'),
        Queue('job.create', routing_key='job.create'),
        Queue('celery', routing_key='celery'),
        Queue('events', routing_key='events'),
        Queue('default', routing_key='default'),
        Queue('repo.sync', Exchange('fanout', 'fanout'), routing_key='repo.sync'),
    )
    app.config['CELERY_ROUTES'] = {
        'create_job': {
            'queue': 'job.create',
            'routing_key': 'job.create',
        },
        'sync_job': {
            'queue': 'job.sync',
            'routing_key': 'job.sync',
        },
        'sync_job_step': {
            'queue': 'job.sync',
            'routing_key': 'job.sync',
        },
        'sync_build': {
            'queue': 'job.sync',
            'routing_key': 'job.sync',
        },
        'check_repos': {
            'queue': 'repo.sync',
            'routing_key': 'repo.sync',
        },
        'sync_repo': {
            'queue': 'repo.sync',
            'routing_key': 'repo.sync',
        },
        'run_event_listener': {
            'queue': 'events',
            'routing_key': 'events',
        },
        'fire_signal': {
            'queue': 'events',
            'routing_key': 'events',
        },
    }

    app.config['EVENT_LISTENERS'] = (
        ('changes.listeners.mail.job_finished_handler', 'job.finished'),
        ('changes.listeners.green_build.build_finished_handler', 'build.finished'),
        ('changes.listeners.hipchat.build_finished_handler', 'build.finished'),
        ('changes.listeners.build_revision.revision_created_handler', 'revision.created'),
    )

    app.config['DEBUG_TB_ENABLED'] = True

    # celerybeat must be running for our cleanup tasks to execute
    # e.g. celery worker -B
    app.config['CELERYBEAT_SCHEDULE'] = {
        'cleanup-tasks': {
            'task': 'cleanup_tasks',
            'schedule': timedelta(minutes=1),
        },
        'check-repos': {
            'task': 'check_repos',
            'schedule': timedelta(minutes=5),
        },
    }
    app.config['CELERY_TIMEZONE'] = 'UTC'

    app.config['SENTRY_DSN'] = None

    app.config['JENKINS_AUTH'] = None
    app.config['JENKINS_URL'] = None
    app.config['JENKINS_TOKEN'] = None

    app.config['KOALITY_URL'] = None
    app.config['KOALITY_API_KEY'] = None

    app.config['GOOGLE_CLIENT_ID'] = None
    app.config['GOOGLE_CLIENT_SECRET'] = None
    app.config['GOOGLE_DOMAIN'] = None

    app.config['REPO_ROOT'] = None

    app.config['MAIL_DEFAULT_SENDER'] = 'changes@localhost'
    app.config['BASE_URI'] = None

    app.config.update(config)

    if _read_config:
        if os.environ.get('CHANGES_CONF'):
            # CHANGES_CONF=/etc/changes.conf.py
            app.config.from_envvar('CHANGES_CONF')
        else:
            # Look for ~/.changes/changes.conf.py
            path = os.path.normpath(os.path.expanduser('~/.changes/changes.conf.py'))
            app.config.from_pyfile(path, silent=True)

    if not app.config['BASE_URI']:
        raise ValueError('You must set ``BASE_URI`` in your configuration.')

    parsed_url = urlparse(app.config['BASE_URI'])
    app.config.setdefault('SERVER_NAME', parsed_url.netloc)
    app.config.setdefault('PREFERRED_URL_SCHEME', parsed_url.scheme)

    if app.debug:
        app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
    else:
        app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 30

    app.url_map.converters['uuid'] = UUIDConverter

    # init sentry first
    sentry.init_app(app)

    @app.before_request
    def capture_user(*args, **kwargs):
        if 'uid' in session:
            sentry.client.user_context({
                'id': session['uid'],
                'email': session['email'],
            })

    api.init_app(app)
    db.init_app(app)
    mail.init_app(app)
    queue.init_app(app)
    redis.init_app(app)
    configure_debug_toolbar(app)

    from raven.contrib.celery import register_signal, register_logger_signal
    register_signal(sentry.client)
    register_logger_signal(sentry.client)

    # configure debug routes first
    if app.debug:
        configure_debug_routes(app)

    configure_templates(app)

    # TODO: these can be moved to wsgi app entrypoints
    configure_api_routes(app)
    configure_web_routes(app)

    configure_jobs(app)

    return app


def configure_debug_toolbar(app):
    toolbar = ChangesDebugToolbarExtension(app)
    return toolbar


def configure_templates(app):
    from changes.utils.times import duration

    app.jinja_env.filters['duration'] = duration


def configure_api_routes(app):
    from changes.api.auth_index import AuthIndexAPIView
    from changes.api.author_build_index import AuthorBuildIndexAPIView
    from changes.api.build_comment_index import BuildCommentIndexAPIView
    from changes.api.build_details import BuildDetailsAPIView
    from changes.api.build_index import BuildIndexAPIView
    from changes.api.build_mark_seen import BuildMarkSeenAPIView
    from changes.api.build_cancel import BuildCancelAPIView
    from changes.api.build_coverage import BuildTestCoverageAPIView
    from changes.api.build_coverage_stats import BuildTestCoverageStatsAPIView
    from changes.api.build_restart import BuildRestartAPIView
    from changes.api.build_retry import BuildRetryAPIView
    from changes.api.build_test_index import BuildTestIndexAPIView
    from changes.api.build_test_index_failures import BuildTestIndexFailuresAPIView
    from changes.api.build_test_index_counts import BuildTestIndexCountsAPIView
    from changes.api.change_details import ChangeDetailsAPIView
    from changes.api.change_index import ChangeIndexAPIView
    from changes.api.cluster_details import ClusterDetailsAPIView
    from changes.api.cluster_index import ClusterIndexAPIView
    from changes.api.cluster_nodes import ClusterNodesAPIView
    from changes.api.job_details import JobDetailsAPIView
    from changes.api.job_log_details import JobLogDetailsAPIView
    from changes.api.jobphase_index import JobPhaseIndexAPIView
    from changes.api.node_details import NodeDetailsAPIView
    from changes.api.node_index import NodeIndexAPIView
    from changes.api.node_job_index import NodeJobIndexAPIView
    from changes.api.patch_details import PatchDetailsAPIView
    from changes.api.plan_details import PlanDetailsAPIView
    from changes.api.plan_index import PlanIndexAPIView
    from changes.api.plan_project_index import PlanProjectIndexAPIView
    from changes.api.plan_step_index import PlanStepIndexAPIView
    from changes.api.project_build_index import ProjectBuildIndexAPIView
    from changes.api.project_build_search import ProjectBuildSearchAPIView
    from changes.api.project_commit_details import ProjectCommitDetailsAPIView
    from changes.api.project_commit_index import ProjectCommitIndexAPIView
    from changes.api.project_coverage_group_index import ProjectCoverageGroupIndexAPIView
    from changes.api.project_index import ProjectIndexAPIView
    from changes.api.project_options_index import ProjectOptionsIndexAPIView
    from changes.api.project_stats import ProjectStatsAPIView
    from changes.api.project_test_details import ProjectTestDetailsAPIView
    from changes.api.project_test_group_index import ProjectTestGroupIndexAPIView
    from changes.api.project_test_index import ProjectTestIndexAPIView
    from changes.api.project_details import ProjectDetailsAPIView
    from changes.api.project_source_details import ProjectSourceDetailsAPIView
    from changes.api.project_source_build_index import ProjectSourceBuildIndexAPIView
    from changes.api.step_details import StepDetailsAPIView
    from changes.api.task_details import TaskDetailsAPIView
    from changes.api.testcase_details import TestCaseDetailsAPIView

    api.add_resource(AuthIndexAPIView, '/auth/')
    api.add_resource(BuildIndexAPIView, '/builds/')
    api.add_resource(AuthorBuildIndexAPIView, '/authors/<author_id>/builds/')
    api.add_resource(BuildCommentIndexAPIView, '/builds/<uuid:build_id>/comments/')
    api.add_resource(BuildDetailsAPIView, '/builds/<uuid:build_id>/')
    api.add_resource(BuildMarkSeenAPIView, '/builds/<uuid:build_id>/mark_seen/')
    api.add_resource(BuildCancelAPIView, '/builds/<uuid:build_id>/cancel/')
    api.add_resource(BuildRestartAPIView, '/builds/<uuid:build_id>/restart/')
    api.add_resource(BuildRetryAPIView, '/builds/<uuid:build_id>/retry/')
    api.add_resource(BuildTestIndexAPIView, '/builds/<uuid:build_id>/tests/')
    api.add_resource(BuildTestIndexFailuresAPIView, '/builds/<uuid:build_id>/tests/failures')
    api.add_resource(BuildTestIndexCountsAPIView, '/builds/<uuid:build_id>/tests/counts')
    api.add_resource(BuildTestCoverageAPIView, '/builds/<uuid:build_id>/coverage/')
    api.add_resource(BuildTestCoverageStatsAPIView, '/builds/<uuid:build_id>/stats/coverage/')
    api.add_resource(ClusterIndexAPIView, '/clusters/')
    api.add_resource(ClusterDetailsAPIView, '/clusters/<uuid:cluster_id>/')
    api.add_resource(ClusterNodesAPIView, '/clusters/<uuid:cluster_id>/nodes/')
    api.add_resource(JobDetailsAPIView, '/jobs/<uuid:job_id>/')
    api.add_resource(JobLogDetailsAPIView, '/jobs/<uuid:job_id>/logs/<uuid:source_id>/')
    api.add_resource(JobPhaseIndexAPIView, '/jobs/<uuid:job_id>/phases/')
    api.add_resource(ChangeIndexAPIView, '/changes/')
    api.add_resource(ChangeDetailsAPIView, '/changes/<uuid:change_id>/')
    api.add_resource(NodeDetailsAPIView, '/nodes/<uuid:node_id>/')
    api.add_resource(NodeIndexAPIView, '/nodes/')
    api.add_resource(NodeJobIndexAPIView, '/nodes/<uuid:node_id>/jobs/')
    api.add_resource(PatchDetailsAPIView, '/patches/<uuid:patch_id>/')
    api.add_resource(PlanIndexAPIView, '/plans/')
    api.add_resource(PlanDetailsAPIView, '/plans/<uuid:plan_id>/')
    api.add_resource(PlanProjectIndexAPIView, '/plans/<uuid:plan_id>/projects/')
    api.add_resource(PlanStepIndexAPIView, '/plans/<uuid:plan_id>/steps/')
    api.add_resource(ProjectIndexAPIView, '/projects/')
    api.add_resource(ProjectDetailsAPIView, '/projects/<project_id>/')
    api.add_resource(ProjectBuildIndexAPIView, '/projects/<project_id>/builds/')
    api.add_resource(ProjectBuildSearchAPIView, '/projects/<project_id>/builds/search/')
    api.add_resource(ProjectCommitIndexAPIView, '/projects/<project_id>/commits/')
    api.add_resource(ProjectCommitDetailsAPIView, '/projects/<project_id>/commits/<commit_id>/')
    api.add_resource(ProjectCoverageGroupIndexAPIView, '/projects/<project_id>/coveragegroups/')
    api.add_resource(ProjectOptionsIndexAPIView, '/projects/<project_id>/options/')
    api.add_resource(ProjectStatsAPIView, '/projects/<project_id>/stats/')
    api.add_resource(ProjectTestIndexAPIView, '/projects/<project_id>/tests/')
    api.add_resource(ProjectTestGroupIndexAPIView, '/projects/<project_id>/testgroups/')
    api.add_resource(ProjectTestDetailsAPIView, '/projects/<project_id>/tests/<test_hash>/')
    api.add_resource(ProjectSourceDetailsAPIView, '/projects/<project_id>/sources/<source_id>/')
    api.add_resource(ProjectSourceBuildIndexAPIView, '/projects/<project_id>/sources/<source_id>/builds/')
    api.add_resource(StepDetailsAPIView, '/steps/<uuid:step_id>/')
    api.add_resource(TestCaseDetailsAPIView, '/tests/<uuid:test_id>/')
    api.add_resource(TaskDetailsAPIView, '/tasks/<uuid:task_id>/')


def configure_web_routes(app):
    from changes.web.auth import AuthorizedView, LoginView, LogoutView
    from changes.web.index import IndexView
    from changes.web.static import StaticView

    if app.debug:
        static_root = os.path.join(PROJECT_ROOT, 'static')
        revision = '0'
    else:
        static_root = os.path.join(PROJECT_ROOT, 'static-built')
        revision = changes.get_revision() or '0'

    app.add_url_rule(
        '/static/' + revision + '/<path:filename>',
        view_func=StaticView.as_view('static', root=static_root))
    app.add_url_rule(
        '/partials/<path:filename>',
        view_func=StaticView.as_view('partials', root=os.path.join(PROJECT_ROOT, 'partials')))

    app.add_url_rule(
        '/auth/login/', view_func=LoginView.as_view('login', authorized_url='authorized'))
    app.add_url_rule(
        '/auth/logout/', view_func=LogoutView.as_view('logout', complete_url='index'))
    app.add_url_rule(
        '/auth/complete/', view_func=AuthorizedView.as_view('authorized', authorized_url='authorized', complete_url='index'))

    app.add_url_rule(
        '/<path:path>', view_func=IndexView.as_view('index-path'))
    app.add_url_rule(
        '/', view_func=IndexView.as_view('index'))


def configure_debug_routes(app):
    from changes.debug.reports.build import BuildReportMailView
    from changes.debug.mail.job_result import JobResultMailView

    app.add_url_rule(
        '/debug/mail/report/build/', view_func=BuildReportMailView.as_view('debug-build-report'))
    app.add_url_rule(
        '/debug/mail/result/job/<job_id>/', view_func=JobResultMailView.as_view('debug-build-result'))


def configure_jobs(app):
    from changes.jobs.check_repos import check_repos
    from changes.jobs.cleanup_tasks import cleanup_tasks
    from changes.jobs.create_job import create_job
    from changes.jobs.signals import (
        fire_signal, run_event_listener
    )
    from changes.jobs.sync_artifact import sync_artifact
    from changes.jobs.sync_build import sync_build
    from changes.jobs.sync_job import sync_job
    from changes.jobs.sync_job_step import sync_job_step
    from changes.jobs.sync_repo import sync_repo
    from changes.jobs.update_project_stats import (
        update_project_stats, update_project_plan_stats)

    queue.register('check_repos', check_repos)
    queue.register('cleanup_tasks', cleanup_tasks)
    queue.register('create_job', create_job)
    queue.register('fire_signal', fire_signal)
    queue.register('run_event_listener', run_event_listener)
    queue.register('sync_artifact', sync_artifact)
    queue.register('sync_build', sync_build)
    queue.register('sync_job', sync_job)
    queue.register('sync_job_step', sync_job_step)
    queue.register('sync_repo', sync_repo)
    queue.register('update_project_stats', update_project_stats)
    queue.register('update_project_plan_stats', update_project_plan_stats)

    @task_postrun.connect
    def cleanup_session(*args, **kwargs):
        """
        Emulate a request cycle for each task to ensure the session objects
        get cleaned up as expected.
        """
        db.session.commit()
        db.session.remove()

    def register_changes_json():
        from kombu.serialization import register
        from kombu.utils.encoding import bytes_t
        from json import dumps, loads
        from uuid import UUID

        def _loads(obj):
            if isinstance(obj, UUID):
                obj = obj.hex
            elif isinstance(obj, bytes_t):
                obj = obj.decode()
            elif isinstance(obj, buffer):
                obj = bytes(obj).decode()
            return loads(obj)

        register('changes_json', dumps, _loads,
                 content_type='application/json',
                 content_encoding='utf-8')

    register_changes_json()
