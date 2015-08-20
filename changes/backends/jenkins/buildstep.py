from __future__ import absolute_import

import logging
import os.path

from datetime import datetime, timedelta
from flask import current_app

from changes.backends.base import UnrecoverableException
from changes.buildsteps.base import BuildStep
from changes.config import db
from changes.constants import Status
from changes.models import SnapshotImage, SnapshotStatus

from .builder import JenkinsBuilder
from .generic_builder import JenkinsGenericBuilder


class JenkinsBuildStep(BuildStep):
    builder_cls = JenkinsBuilder
    logger = logging.getLogger('jenkins')

    def __init__(self, job_name=None, jenkins_url=None, jenkins_diff_url=None,
                 auth_keyname=None, verify=True):
        """
        The JenkinsBuildStep constructor here, which is used as a base
        for all Jenkins builds, only accepts parameters which are used
        to determine where and how to schedule the builds and does not
        deal with any of the logic regarding what to actually schedule
        on those jenkins masters.

        jenkins_url and jenkins_diff_url are either a single url or a list
        of possible jenkins masters for use of queueing. We don't worry
        about which slaves to schedule them on at this level.

        Args:
            auth_keyname: A key in the Changes config file that specifies the
                auth parameter to pass to the requests library. This could be
                a (username, password) tuple, in which case the requests library
                uses HTTPBasicAuth. For details, see http://docs.python-requests.org/en/latest/user/authentication/#basic-authentication
            verify (str or bool): The verify parameter to pass to the requests
                library for verifying SSL certificates. For details,
                see http://docs.python-requests.org/en/latest/user/advanced/#ssl-cert-verification
        """
        # we support a string or a list of strings for master server urls
        if not isinstance(jenkins_url, (list, tuple)):
            if jenkins_url:
                jenkins_url = [jenkins_url]
            else:
                jenkins_url = []

        if not isinstance(jenkins_diff_url, (list, tuple)):
            if jenkins_diff_url:
                jenkins_diff_url = [jenkins_diff_url]
            else:
                jenkins_diff_url = []

        self.job_name = job_name
        self.jenkins_urls = jenkins_url
        self.jenkins_diff_urls = jenkins_diff_url
        self.auth_keyname = auth_keyname
        self.verify = verify

    def get_builder(self, app=current_app, **kwargs):
        """
        Any arguments passed in as kwargs will get passed in to the constructor
        for the builder associated with the buildstep. In particular we use this
        to override build_type.
        """
        args = self.get_builder_options().copy()
        args.update(kwargs)
        return self.builder_cls(app=app, **args)

    def get_builder_options(self):
        """
        A dictionary that is used as kwargs for creating the builder (these can be
        overridden in the kwargs of get_builder but this is not done very commonly),
        so most builder constructor values originate from the get_builder_options
        of the corresponding buildstep or one of its superclasses.
        """
        return {
            'master_urls': self.jenkins_urls,
            'diff_urls': self.jenkins_diff_urls,
            'job_name': self.job_name,
            'verify': self.verify,
            'auth_keyname': self.auth_keyname,
        }

    def get_label(self):
        return 'Execute job "{0}" on Jenkins'.format(self.job_name)

    def execute(self, job):
        """
        Creates a new job using the builder. This is where most of the
        logic is implemented for a given buildstep, but in this case the
        logic is handed to the builder.
        """
        builder = self.get_builder()
        builder.create_job(job)

    def update(self, job):
        builder = self.get_builder()
        builder.sync_job(job)

    def update_step(self, step):
        builder = self.get_builder()
        try:
            builder.sync_step(step)
        except UnrecoverableException:
            # bail if the step has been pending for too long as its likely
            # Jenkins fell over
            if step.date_created < datetime.utcnow() - timedelta(minutes=5):
                return
            raise

    def cancel_step(self, step):
        builder = self.get_builder()
        builder.cancel_step(step)

        step.status = Status.finished
        step.date_finished = datetime.utcnow()
        db.session.add(step)

    def fetch_artifact(self, artifact, **kwargs):
        """
        Processes a single artifact. Critical artifacts - that is, artifacts
        that are somehow special and possibly required - can be specified
        by overriding this method. It is not necessary to super all the way
        to here for critical artifacts, so this implementation is typically only
        used (and always used) for normal artifacts.
        """
        builder = self.get_builder()
        builder.sync_artifact(artifact, **kwargs)

    def can_snapshot(self):
        """
        Since we do most of our build_type logic in the builder rather than
        the buildstep, it makes sense to let the builder determine if it
        can snapshot or not. In particular, this means we have no need to
        actually look up and verify the buildtype from within the buildstep.
        """
        return self.get_builder().can_snapshot()


class JenkinsGenericBuildStep(JenkinsBuildStep):
    builder_cls = JenkinsGenericBuilder

    def __init__(self, job_name, script, cluster, diff_cluster='', path='',
                 workspace='', reset_script='', build_type=None,
                 setup_script='', teardown_script='',
                 snapshot_script=None, **kwargs):
        """
        build_type describes how to use changes-client, but 'legacy'
        defaults to not using it at all. See configuration file
        for more details [CHANGES_CLIENT_BUILD_TYPES]
        workspace can be used to override where to check out the
        source tree and corresponds to the repository root
        once the build starts.

        The cluster and diff cluster arguments refer
        to Jenkins tags that are used to run the builds, so
        it should be made sure that slaves with these tags exist
        for the masters that are being used (See JenkinsBuildStep).

        path is relative to workspace and refers to where to change
        directory to after checking out the repository.

        setup_script, script, and teardown_script represent what to
        actually run. setup_script and teardown_script are always
        executed in the root of the repository (because of limitations
        regarding sharded builds documented elsewhere) while script
        is run from "path". teardown_script is always guaranteed
        to run regardless of whether script runs, but script will not
        run if setup_script fails. snapshot_script runs in place
        of script for snapshot builds.

        reset_script is used to asynchronously reset the workspace.
        """
        self.setup_script = setup_script
        self.script = script
        self.teardown_script = teardown_script
        self.reset_script = reset_script
        self.snapshot_script = snapshot_script
        self.cluster = cluster
        self.diff_cluster = diff_cluster
        self.path = path
        self.workspace = workspace
        self.build_type = build_type

        super(JenkinsGenericBuildStep, self).__init__(job_name=job_name, **kwargs)

    def get_builder_options(self):
        options = super(JenkinsGenericBuildStep, self).get_builder_options()
        options.update({
            'setup_script': self.setup_script,
            'script': self.script,
            'teardown_script': self.teardown_script,
            'reset_script': self.reset_script,
            'snapshot_script': self.snapshot_script,
            'cluster': self.cluster,
            'path': self.path,
            'workspace': self.workspace,
            'diff_cluster': self.diff_cluster,
            'build_type': self.build_type
        })
        return options

    def fetch_artifact(self, artifact, **kwargs):
        # we receive the snapshot images as a json file instead of through
        # the api endpoint because it lets us guarantee that we actually
        # receive the status and we can properly propagate an error
        # if this is not actually the case.
        #
        # we have access to the jobstep in _sync_results so we can determine
        # if the step is a snapshot build or not and from that derive if this
        # json file is required, and give an error if we never find it
        if os.path.basename(artifact.data['fileName']) == 'snapshot_status.json':
            self.update_snapshot_image_status(artifact)
        else:
            super(JenkinsGenericBuildStep, self).fetch_artifact(artifact, **kwargs)

    def update_snapshot_image_status(self, artifact):
        """
        Processes the result of obtaining snapshot_status.json, changing the status
        of the image to what the artifact indicates. snapshot_status.json is expected
        to be a json file with two elements, image (string) and status (string) indicating
        the image id and new status of the image - which is almost always "active" for
        what we use snapshot_status.json for.
        """
        artifact_data = self.get_builder().fetch_artifact(artifact.step, artifact.data)
        status_json = artifact_data.json()
        image_id = status_json['image']
        status = status_json['status']

        image = SnapshotImage.query.get(image_id)
        image.change_status(SnapshotStatus[status])
