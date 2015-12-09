import celery
import changes
import logging
import flask
import os
import os.path
import time
import warnings

from celery.schedules import crontab
from celery.signals import task_postrun
from datetime import timedelta
from flask import request, session
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.assets import Environment
from flask_debugtoolbar import DebugToolbarExtension
from flask_mail import Mail
from kombu import Exchange, Queue
from kombu.common import Broadcast
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
from changes.utils.dirs import enforce_is_subdir

from sqlalchemy import event
from sqlalchemy.orm import Session
# because foo.in_([]) ever executing is a bad idea
from sqlalchemy.exc import SAWarning
warnings.simplefilter('always', SAWarning)
logging.captureWarnings(True)


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
    # required for flask-debugtoolbar and the db perf metrics we record
    app.config['SQLALCHEMY_RECORD_QUERIES'] = True

    app.config['REDIS_URL'] = 'redis://localhost/0'
    app.config['DEBUG'] = True
    app.config['HTTP_PORT'] = 5000
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

    app.config['API_TRACEBACKS'] = True

    # Expiration delay between when a snapshot image becomes superceded and when
    # it becomes truly expired (and thus no longer included in the sync information
    # for any cluster that runs that particular image's plan)
    app.config['CACHED_SNAPSHOT_EXPIRATION_DELTA'] = timedelta(hours=1)

    # default snapshot ID to use when no project-specific active image available
    app.config['DEFAULT_SNAPSHOT'] = None
    app.config['SNAPSHOT_S3_BUCKET'] = None
    app.config['LXC_PRE_LAUNCH'] = None
    app.config['LXC_POST_LAUNCH'] = None

    # Location of artifacts server that is passed to changes-client
    # (include http:// or https://)
    #
    # The default artifact server url uses a random uri which is expected to fail
    # without being overridden. This value is referenced in test code.
    app.config['ARTIFACTS_SERVER'] = 'http://localhost:1234'

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
        Broadcast('repo.update'),
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
        'update_local_repos': {
            'queue': 'repo.update',
        }
    }

    app.config['EVENT_LISTENERS'] = (
        ('changes.listeners.mail.build_finished_handler', 'build.finished'),
        ('changes.listeners.green_build.build_finished_handler', 'build.finished'),
        ('changes.listeners.build_revision.revision_created_handler', 'revision.created'),
        ('changes.listeners.build_finished_notifier.build_finished_handler', 'build.finished'),
        ('changes.listeners.phabricator_listener.build_finished_handler', 'build.finished'),
        ('changes.listeners.analytics_notifier.build_finished_handler', 'build.finished'),
        ('changes.listeners.analytics_notifier.job_finished_handler', 'job.finished'),
        ('changes.listeners.snapshot_build.build_finished_handler', 'build.finished'),
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
            # Hour 7 GMT is midnight PST, hopefully a time of low load
            'schedule': crontab(hour=7, minute=0),
        },
        'update-local-repos': {
            'task': 'update_local_repos',
            'schedule': timedelta(minutes=5),
        }
    }
    app.config['CELERY_TIMEZONE'] = 'UTC'

    app.config['SENTRY_DSN'] = None
    app.config['SENTRY_INCLUDE_PATHS'] = [
        'changes',
    ]

    app.config['KOALITY_URL'] = None
    app.config['KOALITY_API_KEY'] = None

    app.config['GOOGLE_CLIENT_ID'] = None
    app.config['GOOGLE_CLIENT_SECRET'] = None
    app.config['GOOGLE_DOMAIN'] = None

    # must be a URL-safe base64-encoded 32-byte key
    app.config['COOKIE_ENCRYPTION_KEY'] = 'theDefaultKeyIs32BytesLongAndTotallyURLSafe='

    app.config['REPO_ROOT'] = None

    app.config['DEFAULT_FILE_STORAGE'] = 'changes.storage.s3.S3FileStorage'
    app.config['S3_ACCESS_KEY'] = None
    app.config['S3_SECRET_KEY'] = None
    app.config['S3_BUCKET'] = None

    app.config['PHABRICATOR_LINK_HOST'] = None
    app.config['PHABRICATOR_API_HOST'] = None
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

    # Custom changes content unique to your deployment. This is intended to
    # customize the look and feel, provide contextual help and add custom links
    # to other internal tools. You should put your files in webapp/custom and
    # link them here.
    #
    # e.g. /acmecorp-changes/changes.js
    #
    # Some of the custom_content hooks can show images. Assume that the webserver
    # is willing to serve any file within the directory of the js file
    app.config['WEBAPP_CUSTOM_JS'] = None
    # This can be a .less file. We import it after the variables.less,
    # so you can override them in your file
    # Note: if you change this and nothing seems to happen, try deleting
    # webapp/.webassets-cache and bundled.css. This probably won't happen, though
    app.config['WEBAPP_CUSTOM_CSS'] = None

    # In minutes, the timeout applied to jobs without a timeout specified at build time.
    # A timeout should nearly always be specified; this is just a safeguard so that
    # unspecified timeout doesn't mean "is allowed to run indefinitely".
    app.config['DEFAULT_JOB_TIMEOUT_MIN'] = 60

    # Number of milliseconds a transaction can run before triggering a warning.
    app.config['TRANSACTION_MS_WARNING_THRESHOLD'] = 2500

    # Maximum number of jobsteps to retry for a given job
    app.config['JOBSTEP_RETRY_MAX'] = 2

    # we opt these users into the new ui...redirecting them if they
    # hit the homepage
    app.config['NEW_UI_OPTIN_USERS'] = set([])

    # the PHID of the user creating quarantine tasks. We can use this to show
    # the list of open quarantine tasks inline
    app.config['QUARANTINE_PHID'] = None

    # The max length a test's output to be stored. If it is longer, the it will
    # be truncated.
    app.config['TEST_MESSAGE_MAX_LEN'] = 64 * 1024

    app.config['USE_OLD_UI'] = False

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

    # now that config is set up, let's ensure the CUSTOM_JS / CUSTOM_CSS
    # variables are safe (within the changes directory) and convert them to
    # absolute paths
    if app.config['WEBAPP_CUSTOM_CSS']:
        app.config['WEBAPP_CUSTOM_CSS'] = os.path.join(
            PROJECT_ROOT, 'webapp/custom/', app.config['WEBAPP_CUSTOM_CSS'])

        enforce_is_subdir(
            app.config['WEBAPP_CUSTOM_CSS'],
            os.path.join(PROJECT_ROOT, 'webapp/custom'))

    if app.config['WEBAPP_CUSTOM_JS']:
        app.config['WEBAPP_CUSTOM_JS'] = os.path.join(
            PROJECT_ROOT, 'webapp/custom/', app.config['WEBAPP_CUSTOM_JS'])

        enforce_is_subdir(
            app.config['WEBAPP_CUSTOM_JS'],
            os.path.join(PROJECT_ROOT, 'webapp/custom'))

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
    configure_web_routes(app)

    configure_jobs(app)
    configure_transaction_logging(app)

    rules_file = app.config.get('CATEGORIZE_RULES_FILE')
    if rules_file:
        # Fail at startup if we have a bad rules file.
        categorize.load_rules(rules_file)

    import jinja2
    webapp_template_folder = os.path.join(PROJECT_ROOT, 'webapp/html')
    template_folder = os.path.join(PROJECT_ROOT, 'templates')
    template_loader = jinja2.ChoiceLoader([
                app.jinja_loader,
                jinja2.FileSystemLoader([webapp_template_folder, template_folder])
                ])
    app.jinja_loader = template_loader

    return app


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
    from changes.api.build_flaky_tests import BuildFlakyTestsAPIView
    from changes.api.build_index import BuildIndexAPIView
    from changes.api.build_mark_seen import BuildMarkSeenAPIView
    from changes.api.build_cancel import BuildCancelAPIView
    from changes.api.build_coverage import BuildTestCoverageAPIView
    from changes.api.build_coverage_stats import BuildTestCoverageStatsAPIView
    from changes.api.build_restart import BuildRestartAPIView
    from changes.api.build_retry import BuildRetryAPIView
    from changes.api.build_tag import BuildTagAPIView
    from changes.api.build_test_index import BuildTestIndexAPIView
    from changes.api.build_test_index_failures import BuildTestIndexFailuresAPIView
    from changes.api.build_test_index_counts import BuildTestIndexCountsAPIView
    from changes.api.cached_snapshot_cluster_details import CachedSnapshotClusterDetailsAPIView
    from changes.api.cached_snapshot_details import CachedSnapshotDetailsAPIView
    from changes.api.change_details import ChangeDetailsAPIView
    from changes.api.change_index import ChangeIndexAPIView
    from changes.api.cluster_details import ClusterDetailsAPIView
    from changes.api.cluster_index import ClusterIndexAPIView
    from changes.api.cluster_nodes import ClusterNodesAPIView
    from changes.api.command_details import CommandDetailsAPIView
    from changes.api.diff_builds import DiffBuildsIndexAPIView
    from changes.api.diff_build_retry import DiffBuildRetryAPIView
    from changes.api.initial_index import InitialIndexAPIView
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
    from changes.api.kick_sync_repo import KickSyncRepoAPIView
    from changes.api.jenkins_master_blacklist import JenkinsMasterBlacklistAPIView
    from changes.api.node_details import NodeDetailsAPIView
    from changes.api.node_index import NodeIndexAPIView
    from changes.api.node_job_index import NodeJobIndexAPIView
    from changes.api.node_status import NodeStatusAPIView
    from changes.api.adminmessage_index import AdminMessageIndexAPIView
    from changes.api.patch_details import PatchDetailsAPIView
    from changes.api.phabricator_inline import PhabricatorInlineInfoAPIView
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
    from changes.api.quarantine_tasks import QuarantineTasksAPIView
    from changes.api.repository_details import RepositoryDetailsAPIView
    from changes.api.repository_index import RepositoryIndexAPIView
    from changes.api.repository_project_index import RepositoryProjectIndexAPIView
    from changes.api.repository_tree_index import RepositoryTreeIndexAPIView
    from changes.api.snapshot_details import SnapshotDetailsAPIView
    from changes.api.snapshot_index import SnapshotIndexAPIView
    from changes.api.snapshotimage_details import SnapshotImageDetailsAPIView
    from changes.api.snapshot_job_index import SnapshotJobIndexAPIView
    from changes.api.source_details import SourceDetailsAPIView
    from changes.api.source_build_index import SourceBuildIndexAPIView
    from changes.api.step_details import StepDetailsAPIView
    from changes.api.system_stats import SystemStatsAPIView
    from changes.api.task_details import TaskDetailsAPIView
    from changes.api.task_index import TaskIndexAPIView
    from changes.api.testcase_details import TestCaseDetailsAPIView
    from changes.api.user_details import UserDetailsAPIView
    from changes.api.user_index import UserIndexAPIView
    from changes.api.user_options import UserOptionsAPIView
    from changes.api.infra_fail_job_index import InfraFailJobIndexAPIView

    api.add_resource(AuthIndexAPIView, '/auth/')
    api.add_resource(BuildIndexAPIView, '/builds/')
    api.add_resource(AuthorBuildIndexAPIView, '/authors/<author_id>/builds/')
    api.add_resource(AuthorCommitIndexAPIView, '/authors/<author_id>/commits/')
    api.add_resource(AuthorPhabricatorDiffsAPIView, '/authors/<author_id>/diffs/')
    api.add_resource(BuildCommentIndexAPIView, '/builds/<uuid:build_id>/comments/')
    api.add_resource(BuildDetailsAPIView, '/builds/<uuid:build_id>/')
    api.add_resource(BuildFlakyTestsAPIView, '/builds/<uuid:build_id>/flaky_tests/')
    api.add_resource(BuildMarkSeenAPIView, '/builds/<uuid:build_id>/mark_seen/')
    api.add_resource(BuildCancelAPIView, '/builds/<uuid:build_id>/cancel/')
    api.add_resource(BuildRestartAPIView, '/builds/<uuid:build_id>/restart/')
    api.add_resource(BuildRetryAPIView, '/builds/<uuid:build_id>/retry/')
    api.add_resource(BuildTagAPIView, '/builds/<uuid:build_id>/tags')
    api.add_resource(BuildTestIndexAPIView, '/builds/<uuid:build_id>/tests/')
    api.add_resource(BuildTestIndexFailuresAPIView, '/builds/<uuid:build_id>/tests/failures')
    api.add_resource(BuildTestIndexCountsAPIView, '/builds/<uuid:build_id>/tests/counts')
    api.add_resource(BuildTestCoverageAPIView, '/builds/<uuid:build_id>/coverage/')
    api.add_resource(BuildTestCoverageStatsAPIView, '/builds/<uuid:build_id>/stats/coverage/')
    api.add_resource(ClusterIndexAPIView, '/clusters/')
    api.add_resource(ClusterDetailsAPIView, '/clusters/<uuid:cluster_id>/')
    api.add_resource(ClusterNodesAPIView, '/clusters/<uuid:cluster_id>/nodes/')
    api.add_resource(CommandDetailsAPIView, '/commands/<uuid:command_id>/')
    api.add_resource(DiffBuildsIndexAPIView, '/phabricator_diffs/<diff_ident>/builds/')
    api.add_resource(DiffBuildRetryAPIView, '/phabricator_diffs/<diff_id>/retry/')
    api.add_resource(InitialIndexAPIView, '/initial/')
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
    api.add_resource(KickSyncRepoAPIView, '/kick_sync_repo/')
    api.add_resource(ChangeIndexAPIView, '/changes/')
    api.add_resource(ChangeDetailsAPIView, '/changes/<uuid:change_id>/')
    api.add_resource(JenkinsMasterBlacklistAPIView, '/jenkins_master_blacklist/')
    api.add_resource(NodeDetailsAPIView, '/nodes/<uuid:node_id>/')
    api.add_resource(NodeIndexAPIView, '/nodes/')
    api.add_resource(NodeJobIndexAPIView, '/nodes/<uuid:node_id>/jobs/')
    api.add_resource(NodeStatusAPIView, '/nodes/<uuid:node_id>/status/')
    api.add_resource(AdminMessageIndexAPIView, '/messages/')
    api.add_resource(PatchDetailsAPIView, '/patches/<uuid:patch_id>/')
    api.add_resource(PhabricatorInlineInfoAPIView, '/phabricator/inline/')
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
    api.add_resource(QuarantineTasksAPIView, '/quarantine_tasks')
    api.add_resource(RepositoryIndexAPIView, '/repositories/')
    api.add_resource(RepositoryDetailsAPIView, '/repositories/<uuid:repository_id>/')
    api.add_resource(RepositoryProjectIndexAPIView, '/repositories/<uuid:repository_id>/projects/')
    api.add_resource(RepositoryTreeIndexAPIView, '/repositories/<uuid:repository_id>/branches/')
    api.add_resource(SnapshotIndexAPIView, '/snapshots/')
    api.add_resource(SnapshotDetailsAPIView, '/snapshots/<uuid:snapshot_id>/')
    api.add_resource(SnapshotImageDetailsAPIView, '/snapshotimages/<uuid:image_id>/')
    api.add_resource(CachedSnapshotClusterDetailsAPIView, '/snapshots/cache/clusters/<cluster>/')
    api.add_resource(CachedSnapshotDetailsAPIView, '/snapshots/<uuid:snapshot_id>/cache/')
    api.add_resource(SnapshotJobIndexAPIView, '/snapshots/<uuid:snapshot_id>/jobs/')
    api.add_resource(InfraFailJobIndexAPIView, '/admin_dash/infra_fail_jobs/')
    api.add_resource(SourceDetailsAPIView, '/sources/<source_id>/')
    api.add_resource(SourceBuildIndexAPIView, '/sources_builds/')
    api.add_resource(SystemStatsAPIView, '/systemstats/')
    api.add_resource(StepDetailsAPIView, '/steps/<uuid:step_id>/')
    api.add_resource(TestCaseDetailsAPIView, '/tests/<uuid:test_id>/')
    api.add_resource(TaskIndexAPIView, '/tasks/')
    api.add_resource(TaskDetailsAPIView, '/tasks/<uuid:task_id>/')
    api.add_resource(UserIndexAPIView, '/users/')
    api.add_resource(UserDetailsAPIView, '/users/<uuid:user_id>/')
    api.add_resource(UserOptionsAPIView, '/user_options/')
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
        '/auth/login/', view_func=LoginView.as_view('login', authorized_url='authorized'))
    app.add_url_rule(
        '/auth/logout/', view_func=LogoutView.as_view('logout', complete_url='index'))
    app.add_url_rule(
        '/auth/complete/', view_func=AuthorizedView.as_view('authorized',
                                                            complete_url='index',
                                                            authorized_url='authorized',
                                                            ))

    if app.config['USE_OLD_UI']:
        app.add_url_rule(
            '/static/' + revision + '/<path:filename>',
            view_func=StaticView.as_view('static', root=static_root))
        app.add_url_rule(
            '/partials/<path:filename>',
            view_func=StaticView.as_view('partials', root=os.path.join(PROJECT_ROOT, 'partials')))
        app.add_url_rule(
            '/<path:path>', view_func=IndexView.as_view('index-path'))
        app.add_url_rule(
            '/', view_func=IndexView.as_view('index'))
    else:
        configure_default(app)


def configure_default(app):
    from changes.web.index import IndexView
    from changes.web.static import StaticView

    static_root = os.path.join(PROJECT_ROOT, 'webapp')
    revision_facts = changes.get_revision_info() or {}
    revision = revision_facts.get('hash', '0') if not app.debug else '0'

    # static file paths contain the current revision so that users
    # don't hit outdated static resources
    hacky_vendor_root = os.path.join(PROJECT_ROOT, 'static')
    app.add_url_rule(
        '/static/' + revision + '/<path:filename>',
        view_func=StaticView.as_view(
            'static',
            root=static_root,
            hacky_vendor_root=hacky_vendor_root)
    )

    app.add_url_rule('/<path:path>',
      view_func=IndexView.as_view('index-path', use_v2=True))
    app.add_url_rule('/', view_func=IndexView.as_view('index', use_v2=True))

    # serve custom images if we have a custom content file
    if app.config['WEBAPP_CUSTOM_JS']:
        custom_dir = os.path.dirname(app.config['WEBAPP_CUSTOM_JS'])
        app.add_url_rule(
            '/custom_image/<path:filename>',
            view_func=StaticView.as_view(
                'custom_image',
                root=custom_dir)
        )

    # One last thing...we use CSS bundling via flask-assets, so set that up on
    # the main app object
    assets = Environment(app)
    assets.config['directory'] = os.path.join(PROJECT_ROOT, 'webapp')
    assets.config['url'] = '/static/' + revision + '/'
    # path to the lessc binary.
    assets.config['LESS_BIN'] = os.path.join(PROJECT_ROOT, 'node_modules/.bin/lessc')

    assets.config['LESS_EXTRA_ARGS'] = (['--global-var=custom_css="%s"' % app.config['WEBAPP_CUSTOM_CSS']]
        if app.config['WEBAPP_CUSTOM_CSS']
        else [])

    assets.load_path = [
        os.path.join(PROJECT_ROOT, 'webapp')
    ]


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
    from changes.jobs.update_local_repos import update_local_repos

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
    queue.register('update_local_repos', update_local_repos)

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


def configure_transaction_logging(app):
    """Add sqlalchemy transaction event listeners to detect long running transactions.

    The timer starts after a transaction has started (and database resources are being used)
    and ends after a commit or rollback.
    This currently only warns if a transaction takes longer than `TRANSACTION_MS_WARNING_THRESHOLD`
    in the app config but this can be extended to log stats or other information
    about transactions.
    """

    @event.listens_for(Session, 'after_begin')
    def log_transaction_begin(session, transaction, connection):
        session.info['txn_start_time'] = time.time()

    @event.listens_for(Session, 'after_commit')
    def log_transaction_commit(session):
        _log_transaction_end(session)

    @event.listens_for(Session, 'after_rollback')
    def log_transaction_rollback(session):
        _log_transaction_end(session)

    def _get_txn_context():
        current_task = celery.current_task
        if current_task:
            return "task_%s" % (current_task.name,)
        elif flask.has_request_context():
            return "request_%s" % (request.endpoint,)
        else:
            return "unknown"

    def _log_transaction_end(session):
        context_name = _get_txn_context()
        if 'txn_start_time' in session.info:
            txn_start_time = session.info.pop('txn_start_time')
            txn_end_time = time.time()
            time_taken_ms = 1000 * (txn_end_time - txn_start_time)
            if time_taken_ms > app.config['TRANSACTION_MS_WARNING_THRESHOLD']:
                logging.warning("Long running transaction in %s took %dms.",
                                context_name, time_taken_ms)
