import changes
import logging
import flask
import os
import os.path
import warnings

from celery.schedules import crontab
from celery.signals import task_postrun
from datetime import timedelta
from flask import request, session, Blueprint
from flask.ext.sqlalchemy import SQLAlchemy
from flask_debugtoolbar import DebugToolbarExtension
from flask_mail import Mail
from kombu import Exchange, Queue
from raven.contrib.flask import Sentry
from urlparse import urlparse
from werkzeug.contrib.fixers import ProxyFix

from changes.constants import PROJECT_ROOT
from changes.api.controller import APIController, APICatchall
from changes.experimental import categorize
from changes.ext.celery import Celery
from changes.ext.redis import Redis
from changes.ext.statsreporter import StatsReporter
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
statsreporter = StatsReporter()
sentry = Sentry(logging=True, level=logging.WARN)


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

    # default snapshot ID to use when no project-specific active image available
    app.config['DEFAULT_SNAPSHOT'] = None
    app.config['SNAPSHOT_S3_BUCKET'] = None
    app.config['LXC_PRE_LAUNCH'] = None
    app.config['LXC_POST_LAUNCH'] = None

    app.config['CHANGES_CLIENT_DEFAULT_BUILD_TYPE'] = 'legacy'

    # This is a hash from each build type (string identifiers used in
    # build step configuration) to a "build spec", a definition of
    # how to use changes-client to build. To use changes-client, the key
    # 'uses_client' must be set to True.
    #
    # Required build spec keys for client:
    #   adapter -> basic or lxc
    #   jenkins-command -> command to run from jenkins directly ($JENKINS_COMMAND)
    #   commands -> array of hash from script -> string that represents a script
    #
    # Optional keys (lxc-only)
    #   pre-launch -> lxc pre-launch script
    #   post-launch -> lxc post-launch script
    #   release -> lxc release
    app.config['CHANGES_CLIENT_BUILD_TYPES'] = {
        'legacy': {'uses_client': False},
    }

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

    # By default, Celery logs writes to stdout/stderr as WARNING, which
    # is a bit harsh considering that some of the code is code we don't
    # own calling 'print'. This flips the default back to INFO, which seems
    # more appropriate. Can be overridden by the Changes config.
    app.config['CELERY_REDIRECT_STDOUTS_LEVEL'] = 'INFO'

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
        ('changes.listeners.mail.build_finished_handler', 'build.finished'),
        ('changes.listeners.green_build.build_finished_handler', 'build.finished'),
        ('changes.listeners.build_revision.revision_created_handler', 'revision.created'),
        ('changes.listeners.build_finished_notifier.build_finished_handler', 'build.finished'),
        ('changes.listeners.phabricator_listener.build_finished_handler', 'build.finished'),
        ('changes.listeners.analytics_notifier.build_finished_handler', 'build.finished'),
        ('changes.listeners.analytics_notifier.job_finished_handler', 'job.finished'),
    )

    # restrict outbound notifications to the given domains
    app.config['MAIL_DOMAIN_WHITELIST'] = ()

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
            'schedule': timedelta(minutes=2),
        },
        'aggregate-flaky-tests': {
            'task': 'aggregate_flaky_tests',
            'schedule': crontab(hour=0, minute=0),
        },
    }
    app.config['CELERY_TIMEZONE'] = 'UTC'

    app.config['SENTRY_DSN'] = None
    app.config['SENTRY_INCLUDE_PATHS'] = [
        'changes',
    ]

    app.config['JENKINS_AUTH'] = None
    app.config['JENKINS_URL'] = None
    app.config['JENKINS_TOKEN'] = None
    app.config['JENKINS_CLUSTERS'] = {}

    app.config['KOALITY_URL'] = None
    app.config['KOALITY_API_KEY'] = None

    app.config['GOOGLE_CLIENT_ID'] = None
    app.config['GOOGLE_CLIENT_SECRET'] = None
    app.config['GOOGLE_DOMAIN'] = None

    app.config['REPO_ROOT'] = None

    app.config['DEFAULT_FILE_STORAGE'] = 'changes.storage.s3.S3FileStorage'
    app.config['S3_ACCESS_KEY'] = None
    app.config['S3_SECRET_KEY'] = None
    app.config['S3_BUCKET'] = None

    app.config['PHABRICATOR_HOST'] = None
    app.config['PHABRICATOR_USERNAME'] = None
    app.config['PHABRICATOR_CERT'] = None

    app.config['MAIL_DEFAULT_SENDER'] = 'changes@localhost'
    app.config['BASE_URI'] = 'http://localhost:5000'

    # if set to a string, most (all?) of the frontend js will make API calls
    # to the host this string is set to (e.g. http://changes.bigcompany.com)
    # THIS IS JUST FOR EASIER TESTING IN DEVELOPMENT. Although it won't even
    # work in prod: you'll have to start chrome with --disable-web-security to
    # make this work. Override this this in your changes.conf.py file
    app.config['WEBAPP_USE_ANOTHER_HOST'] = None

    # points to a file with custom changes content unique to your deployment.
    # Link to internal tools, provide inline contextual help on your development
    # process, etc.
    # e.g. /mycompany/config/changes_content.js
    app.config['WEBAPP_CUSTOMIZED_CONTENT_FILE'] = None

    # In minutes, the timeout applied to jobs without a timeout specified at build time.
    # A timeout should nearly always be specified; this is just a safeguard so that
    # unspecified timeout doesn't mean "is allowed to run indefinitely".
    app.config['DEFAULT_JOB_TIMEOUT_MIN'] = 60

    app.config.update(config)
    if _read_config:
        if os.environ.get('CHANGES_CONF'):
            # CHANGES_CONF=/etc/changes.conf.py
            app.config.from_envvar('CHANGES_CONF')
        else:
            # Look for ~/.changes/changes.conf.py
            path = os.path.normpath(os.path.expanduser('~/.changes/changes.conf.py'))
            app.config.from_pyfile(path, silent=True)

    # default the DSN for changes-client to the server's DSN
    app.config.setdefault('CLIENT_SENTRY_DSN', app.config['SENTRY_DSN'])

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
    statsreporter.init_app(app)

    configure_debug_toolbar(app)

    from raven.contrib.celery import register_signal, register_logger_signal
    register_signal(sentry.client)
    register_logger_signal(sentry.client, loglevel=logging.WARNING)

    # configure debug routes first
    if app.debug:
        configure_debug_routes(app)

    configure_templates(app)

    # TODO: these can be moved to wsgi app entrypoints
    configure_api_routes(app)
    app_static_root = configure_web_routes(app)

    # blueprint for our new v2 webapp
    blueprint = create_v2_blueprint(app, app_static_root)
    app.register_blueprint(blueprint, url_prefix='/v2')

    configure_jobs(app)

    rules_file = app.config.get('CATEGORIZE_RULES_FILE')
    if rules_file:
        # Fail at startup if we have a bad rules file.
        categorize.load_rules(rules_file)

    return app


def create_v2_blueprint(app, app_static_root):
    blueprint = Blueprint(
        'webapp_v2',
        __name__,
        template_folder=os.path.join(PROJECT_ROOT, 'webapp/html')
    )

    from changes.web.index import IndexView
    from changes.web.static import StaticView

    # TODO: set revision to the current git hash once we add prod static
    # resource compilation back in to v2
    static_root = os.path.join(PROJECT_ROOT, 'webapp')
    revision = '0'

    # TODO: have non-debug mode use webapp/dist, once I figure out how to
    # compile with babel

    # all of these urls are automatically prefixed with v2
    # (see the register_blueprint call above)

    blueprint.add_url_rule(
        '/static/' + revision + '/<path:filename>',
        view_func=StaticView.as_view(
            'static',
            root=static_root,
            hacky_vendor_root=app_static_root)
    )

    if app.config['WEBAPP_CUSTOMIZED_CONTENT_FILE']:
        content_dir = os.path.dirname(app.config['WEBAPP_CUSTOMIZED_CONTENT_FILE'])
        # StaticView wants a filename, so we send the filename down to js
        # and have it request this path
        blueprint.add_url_rule(
            '/customized_content/<path:filename>',
            view_func=StaticView.as_view(
                'custom_content',
                root=content_dir)
        )

    # no need to set up our own login/logout urls

    blueprint.add_url_rule('/<path:path>',
      view_func=IndexView.as_view('index-path', use_v2=True))
    blueprint.add_url_rule('/', view_func=IndexView.as_view('index', use_v2=True))
    return blueprint


def configure_debug_toolbar(app):
    toolbar = ChangesDebugToolbarExtension(app)
    return toolbar


def configure_templates(app):
    from changes.utils.times import duration
    from changes.utils.text import break_long_lines, nl2br

    app.jinja_env.filters['duration'] = duration
    app.jinja_env.filters['break_long_lines'] = break_long_lines
    app.jinja_env.filters['nl2br'] = nl2br


def configure_api_routes(app):
    from changes.api.auth_index import AuthIndexAPIView
    from changes.api.author_build_index import AuthorBuildIndexAPIView
    from changes.api.author_commit_index import AuthorCommitIndexAPIView
    from changes.api.author_diffs import AuthorPhabricatorDiffsAPIView
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
    from changes.api.command_details import CommandDetailsAPIView
    from changes.api.diff_build_retry import DiffBuildRetryAPIView
    from changes.api.job_artifact_index import JobArtifactIndexAPIView
    from changes.api.job_details import JobDetailsAPIView
    from changes.api.job_log_details import JobLogDetailsAPIView
    from changes.api.jobphase_index import JobPhaseIndexAPIView
    from changes.api.jobstep_allocate import JobStepAllocateAPIView
    from changes.api.jobstep_artifacts import JobStepArtifactsAPIView
    from changes.api.jobstep_deallocate import JobStepDeallocateAPIView
    from changes.api.jobstep_details import JobStepDetailsAPIView
    from changes.api.jobstep_heartbeat import JobStepHeartbeatAPIView
    from changes.api.jobstep_log_append import JobStepLogAppendAPIView
    from changes.api.log_client_perf import LogClientPerfAPIView
    from changes.api.node_details import NodeDetailsAPIView
    from changes.api.node_index import NodeIndexAPIView
    from changes.api.node_job_index import NodeJobIndexAPIView
    from changes.api.node_status import NodeStatusAPIView
    from changes.api.adminmessage_index import AdminMessageIndexAPIView
    from changes.api.patch_details import PatchDetailsAPIView
    from changes.api.phabricator_notify_diff import PhabricatorNotifyDiffAPIView
    from changes.api.plan_details import PlanDetailsAPIView
    from changes.api.plan_options import PlanOptionsAPIView
    from changes.api.plan_step_index import PlanStepIndexAPIView
    from changes.api.project_build_index import ProjectBuildIndexAPIView
    from changes.api.project_commit_builds import ProjectCommitBuildsAPIView
    from changes.api.project_commit_details import ProjectCommitDetailsAPIView
    from changes.api.project_commit_index import ProjectCommitIndexAPIView
    from changes.api.project_coverage_index import ProjectCoverageIndexAPIView
    from changes.api.project_coverage_group_index import ProjectCoverageGroupIndexAPIView
    from changes.api.project_flaky_tests import ProjectFlakyTestsAPIView
    from changes.api.project_index import ProjectIndexAPIView
    from changes.api.project_latest_green_builds import ProjectLatestGreenBuildsAPIView
    from changes.api.project_options_index import ProjectOptionsIndexAPIView
    from changes.api.project_plan_index import ProjectPlanIndexAPIView
    from changes.api.project_snapshot_index import ProjectSnapshotIndexAPIView
    from changes.api.project_stats import ProjectStatsAPIView
    from changes.api.project_test_details import ProjectTestDetailsAPIView
    from changes.api.project_test_group_index import ProjectTestGroupIndexAPIView
    from changes.api.project_test_history import ProjectTestHistoryAPIView
    from changes.api.project_test_index import ProjectTestIndexAPIView
    from changes.api.project_details import ProjectDetailsAPIView
    from changes.api.project_source_details import ProjectSourceDetailsAPIView
    from changes.api.project_source_build_index import ProjectSourceBuildIndexAPIView
    from changes.api.repository_details import RepositoryDetailsAPIView
    from changes.api.repository_index import RepositoryIndexAPIView
    from changes.api.repository_project_index import RepositoryProjectIndexAPIView
    from changes.api.repository_tree_index import RepositoryTreeIndexAPIView
    from changes.api.snapshot_details import SnapshotDetailsAPIView
    from changes.api.snapshot_index import SnapshotIndexAPIView
    from changes.api.snapshotimage_details import SnapshotImageDetailsAPIView
    from changes.api.step_details import StepDetailsAPIView
    from changes.api.system_stats import SystemStatsAPIView
    from changes.api.task_details import TaskDetailsAPIView
    from changes.api.task_index import TaskIndexAPIView
    from changes.api.testcase_details import TestCaseDetailsAPIView
    from changes.api.user_details import UserDetailsAPIView
    from changes.api.user_index import UserIndexAPIView

    api.add_resource(AuthIndexAPIView, '/auth/')
    api.add_resource(BuildIndexAPIView, '/builds/')
    api.add_resource(AuthorBuildIndexAPIView, '/authors/<author_id>/builds/')
    api.add_resource(AuthorCommitIndexAPIView, '/authors/<author_id>/commits/')
    api.add_resource(AuthorPhabricatorDiffsAPIView, '/authors/<author_id>/diffs/')
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
    api.add_resource(CommandDetailsAPIView, '/commands/<uuid:command_id>/')
    api.add_resource(DiffBuildRetryAPIView, '/phabricator_diffs/<diff_id>/retry/')
    api.add_resource(JobDetailsAPIView, '/jobs/<uuid:job_id>/')
    api.add_resource(JobLogDetailsAPIView, '/jobs/<uuid:job_id>/logs/<uuid:source_id>/')
    api.add_resource(JobPhaseIndexAPIView, '/jobs/<uuid:job_id>/phases/')
    api.add_resource(JobArtifactIndexAPIView, '/jobs/<uuid:job_id>/artifacts/')
    api.add_resource(JobStepAllocateAPIView, '/jobsteps/allocate/')
    api.add_resource(JobStepDetailsAPIView, '/jobsteps/<uuid:step_id>/')
    api.add_resource(JobStepArtifactsAPIView, '/jobsteps/<uuid:step_id>/artifacts/')
    api.add_resource(JobStepDeallocateAPIView, '/jobsteps/<uuid:step_id>/deallocate/')
    api.add_resource(JobStepHeartbeatAPIView, '/jobsteps/<uuid:step_id>/heartbeat/')
    api.add_resource(JobStepLogAppendAPIView, '/jobsteps/<uuid:step_id>/logappend/')
    api.add_resource(LogClientPerfAPIView, '/perf/')
    api.add_resource(ChangeIndexAPIView, '/changes/')
    api.add_resource(ChangeDetailsAPIView, '/changes/<uuid:change_id>/')
    api.add_resource(NodeDetailsAPIView, '/nodes/<uuid:node_id>/')
    api.add_resource(NodeIndexAPIView, '/nodes/')
    api.add_resource(NodeJobIndexAPIView, '/nodes/<uuid:node_id>/jobs/')
    api.add_resource(NodeStatusAPIView, '/nodes/<uuid:node_id>/status/')
    api.add_resource(AdminMessageIndexAPIView, '/messages/')
    api.add_resource(PatchDetailsAPIView, '/patches/<uuid:patch_id>/')
    api.add_resource(PhabricatorNotifyDiffAPIView, '/phabricator/notify-diff/')
    api.add_resource(PlanDetailsAPIView, '/plans/<uuid:plan_id>/')
    api.add_resource(PlanOptionsAPIView, '/plans/<uuid:plan_id>/options/')
    api.add_resource(PlanStepIndexAPIView, '/plans/<uuid:plan_id>/steps/')
    api.add_resource(ProjectIndexAPIView, '/projects/')
    api.add_resource(ProjectDetailsAPIView, '/projects/<project_id>/')
    api.add_resource(ProjectBuildIndexAPIView, '/projects/<project_id>/builds/')
    api.add_resource(ProjectBuildIndexAPIView, '/projects/<project_id>/builds/search/',
                     endpoint='projectbuildsearchapiview')
    api.add_resource(ProjectLatestGreenBuildsAPIView, '/projects/<project_id>/latest_green_builds/')
    api.add_resource(ProjectCommitIndexAPIView, '/projects/<project_id>/commits/')
    api.add_resource(ProjectCommitDetailsAPIView, '/projects/<project_id>/commits/<commit_id>/')
    api.add_resource(ProjectCommitBuildsAPIView, '/projects/<project_id>/commits/<commit_id>/builds/')
    api.add_resource(ProjectCoverageIndexAPIView, '/projects/<project_id>/coverage/')
    api.add_resource(ProjectCoverageGroupIndexAPIView, '/projects/<project_id>/coveragegroups/')
    api.add_resource(ProjectFlakyTestsAPIView, '/projects/<project_id>/flaky_tests/')
    api.add_resource(ProjectOptionsIndexAPIView, '/projects/<project_id>/options/')
    api.add_resource(ProjectPlanIndexAPIView, '/projects/<project_id>/plans/')
    api.add_resource(ProjectSnapshotIndexAPIView, '/projects/<project_id>/snapshots/')
    api.add_resource(ProjectStatsAPIView, '/projects/<project_id>/stats/')
    api.add_resource(ProjectTestIndexAPIView, '/projects/<project_id>/tests/')
    api.add_resource(ProjectTestGroupIndexAPIView, '/projects/<project_id>/testgroups/')
    api.add_resource(ProjectTestDetailsAPIView, '/projects/<project_id>/tests/<test_hash>/')
    api.add_resource(ProjectTestHistoryAPIView, '/projects/<project_id>/tests/<test_hash>/history/')
    api.add_resource(ProjectSourceDetailsAPIView, '/projects/<project_id>/sources/<source_id>/')
    api.add_resource(ProjectSourceBuildIndexAPIView, '/projects/<project_id>/sources/<source_id>/builds/')
    api.add_resource(RepositoryIndexAPIView, '/repositories/')
    api.add_resource(RepositoryDetailsAPIView, '/repositories/<uuid:repository_id>/')
    api.add_resource(RepositoryProjectIndexAPIView, '/repositories/<uuid:repository_id>/projects/')
    api.add_resource(RepositoryTreeIndexAPIView, '/repositories/<uuid:repository_id>/branches/')
    api.add_resource(SnapshotIndexAPIView, '/snapshots/')
    api.add_resource(SnapshotDetailsAPIView, '/snapshots/<uuid:snapshot_id>/')
    api.add_resource(SnapshotImageDetailsAPIView, '/snapshotimages/<uuid:image_id>/')
    api.add_resource(SystemStatsAPIView, '/systemstats/')
    api.add_resource(StepDetailsAPIView, '/steps/<uuid:step_id>/')
    api.add_resource(TestCaseDetailsAPIView, '/tests/<uuid:test_id>/')
    api.add_resource(TaskIndexAPIView, '/tasks/')
    api.add_resource(TaskDetailsAPIView, '/tasks/<uuid:task_id>/')
    api.add_resource(UserIndexAPIView, '/users/')
    api.add_resource(UserDetailsAPIView, '/users/<uuid:user_id>/')
    api.add_resource(APICatchall, '/<path:path>')


def configure_web_routes(app):
    from changes.web.auth import AuthorizedView, LoginView, LogoutView
    from changes.web.index import IndexView
    from changes.web.static import StaticView

    # the path used by the webapp for static resources uses the current app
    # version (which is a git hash) so that browsers don't use an old, cached
    # versions of those resources

    if app.debug:
        static_root = os.path.join(PROJECT_ROOT, 'static')
        revision = '0'
    else:
        static_root = os.path.join(PROJECT_ROOT, 'static-built')
        revision_facts = changes.get_revision_info() or {}
        revision = revision_facts.get('hash', '0')

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
        '/auth/complete/', view_func=AuthorizedView.as_view('authorized',
                                                            complete_url='index',
                                                            authorized_url='authorized',
                                                            ))

    app.add_url_rule(
        '/<path:path>', view_func=IndexView.as_view('index-path'))
    app.add_url_rule(
        '/', view_func=IndexView.as_view('index'))

    # bit of a hack: we use this for creating the v2 blueprint
    return static_root


def configure_debug_routes(app):
    from changes.debug.reports.build import BuildReportMailView
    from changes.debug.mail.build_result import BuildResultMailView

    app.add_url_rule(
        '/debug/mail/report/build/', view_func=BuildReportMailView.as_view('debug-build-report'))
    app.add_url_rule(
        '/debug/mail/result/build/<build_id>/', view_func=BuildResultMailView.as_view('debug-build-result'))


def configure_jobs(app):
    from changes.jobs.flaky_tests import aggregate_flaky_tests
    from changes.jobs.check_repos import check_repos
    from changes.jobs.cleanup_tasks import cleanup_tasks
    from changes.jobs.create_job import create_job
    from changes.jobs.import_repo import import_repo
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

    queue.register('aggregate_flaky_tests', aggregate_flaky_tests)
    queue.register('check_repos', check_repos)
    queue.register('cleanup_tasks', cleanup_tasks)
    queue.register('create_job', create_job)
    queue.register('fire_signal', fire_signal)
    queue.register('import_repo', import_repo)
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
