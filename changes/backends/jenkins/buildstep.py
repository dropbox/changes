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

    def __init__(self, job_name=None, jenkins_url=None, jenkins_diff_url=None, token=None, auth=None):
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
        self.token = token
        self.auth = auth

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
        return {
            'master_urls': self.jenkins_urls,
            'diff_urls': self.jenkins_diff_urls,
            'token': self.token,
            'auth': self.auth,
            'job_name': self.job_name,
        }

    def get_label(self):
        return 'Execute job "{0}" on Jenkins'.format(self.job_name)

    def execute(self, job):
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
        builder = self.get_builder()
        builder.sync_artifact(artifact, **kwargs)

    def can_snapshot(self):
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

        Scripts:
          - setup script: Runs before script
          - teardown script: Runs after script
          - reset script: Runs after build async
          - snapshot cript: Replaces script for snapshot builds
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
        artifact_data = self.get_builder().fetch_artifact(artifact.step, artifact.data)
        status_json = artifact_data.json()
        image_id = status_json['image']
        status = status_json['status']

        image = SnapshotImage.query.get(image_id)
        image.change_status(SnapshotStatus[status])
