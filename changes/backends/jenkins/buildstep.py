from __future__ import absolute_import

from datetime import datetime, timedelta
from flask import current_app

from changes.backends.base import UnrecoverableException
from changes.buildsteps.base import BuildStep

from .builder import JenkinsBuilder
from .factory_builder import JenkinsFactoryBuilder
from .generic_builder import JenkinsGenericBuilder


class JenkinsBuildStep(BuildStep):
    builder_cls = JenkinsBuilder

    def __init__(self, job_name=None, jenkins_url=None, token=None, auth=None):
        self.job_name = job_name
        self.jenkins_url = jenkins_url
        self.token = token
        self.auth = auth

    def get_builder(self, app=current_app):
        return self.builder_cls(app=app, **self.get_builder_options())

    def get_builder_options(self):
        return {
            'base_url': self.jenkins_url,
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

    def cancel(self, job):
        builder = self.get_builder()
        builder.cancel_job(job)

    def fetch_artifact(self, step, artifact):
        builder = self.get_builder()
        builder.sync_artifact(step, artifact)


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

    def __init__(self, job_name, script, cluster, path='', **kwargs):
        self.script = script
        self.cluster = cluster
        self.path = path
        super(JenkinsGenericBuildStep, self).__init__(job_name=job_name, **kwargs)

    def get_builder_options(self):
        options = super(JenkinsGenericBuildStep, self).get_builder_options()
        options.update({
            'script': self.script,
            'cluster': self.cluster,
            'path': self.path,
        })
        return options
