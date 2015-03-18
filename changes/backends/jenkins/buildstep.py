from __future__ import absolute_import

import logging

from datetime import datetime, timedelta
from flask import current_app

from changes.backends.base import UnrecoverableException
from changes.buildsteps.base import BuildStep
from changes.config import db
from changes.constants import Status

from .builder import JenkinsBuilder
from .factory_builder import JenkinsFactoryBuilder
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

    def get_builder(self, app=current_app):
        return self.builder_cls(app=app, **self.get_builder_options())

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


class JenkinsFactoryBuildStep(JenkinsBuildStep):
    builder_cls = JenkinsFactoryBuilder

    def __init__(self, downstream_job_names=(), **kwargs):
        self.downstream_job_names = downstream_job_names
        super(JenkinsFactoryBuildStep, self).__init__(**kwargs)

    def get_builder_options(self):
        options = super(JenkinsFactoryBuildStep, self).get_builder_options()
        options['downstream_job_names'] = self.downstream_job_names
        return options


class JenkinsGenericBuildStep(JenkinsBuildStep):
    builder_cls = JenkinsGenericBuilder

    def __init__(self, job_name, script, cluster, diff_cluster='', path='',
                 workspace='', reset_script='', **kwargs):
        self.script = script
        self.reset_script = reset_script
        self.cluster = cluster
        self.diff_cluster = diff_cluster
        self.path = path
        self.workspace = workspace

        super(JenkinsGenericBuildStep, self).__init__(job_name=job_name, **kwargs)

    def get_builder_options(self):
        options = super(JenkinsGenericBuildStep, self).get_builder_options()
        options.update({
            'script': self.script,
            'reset_script': self.reset_script,
            'cluster': self.cluster,
            'path': self.path,
            'workspace': self.workspace,
            'diff_cluster': self.diff_cluster,
        })
        return options
