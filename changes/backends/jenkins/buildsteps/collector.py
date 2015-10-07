from __future__ import absolute_import

import os.path

from hashlib import md5

from changes.backends.jenkins.buildstep import JenkinsGenericBuildStep
from changes.backends.jenkins.generic_builder import JenkinsGenericBuilder
from changes.buildsteps.base import BuildStep
from changes.config import db
from changes.constants import Result, Status
from changes.db.utils import get_or_create, try_create
from changes.jobs.sync_job_step import sync_job_step
from changes.models import FailureReason, JobPhase, JobStep


class JenkinsCollectorBuilder(JenkinsGenericBuilder):
    def get_default_job_phase_label(self, job, job_data):
        return 'Collect Jobs'

    def get_required_artifact(self):
        """The initial (collect) step must return at least one artifact with
        this filename, or it will be marked as failed.

        Returns:
            str: the required filename
        """
        return 'jobs.json'

    def _sync_results(self, step, item):
        """
        At this point, we have already collected all of the artifacts, so if
        this is the initial collection phase and we did not collect a
        critical artifact then we error.
        """
        super(JenkinsCollectorBuilder, self)._sync_results(step, item)

        # We annotate the "expanded" jobs with this tag, so the individual
        # shards will no longer require the critical artifact
        if step.data.get('expanded'):
            return

        expected_image = self.get_expected_image(step.job_id)

        # if this is a snapshot build then we don't have to worry about
        # sanity checking the normal artifacts
        if expected_image:
            return

        artifacts = item.get('artifacts', ())
        required_artifact = self.get_required_artifact()

        if not any(os.path.basename(a['fileName']) == required_artifact for a in artifacts):
            step.result = Result.failed
            db.session.add(step)

            job = step.job
            try_create(FailureReason, {
                'step_id': step.id,
                'job_id': job.id,
                'build_id': job.build_id,
                'project_id': job.project_id,
                'reason': 'missing_artifact'
            })


class JenkinsCollectorBuildStep(JenkinsGenericBuildStep):
    """
    Fires off a generic job with parameters:

        CHANGES_BID = UUID
        CHANGES_PID = project slug
        REPO_URL    = repository URL
        REPO_VCS    = hg/git
        REVISION    = sha/id of revision
        PATCH_URL   = patch to apply, if available
        SCRIPT      = command to run

    A "jobs.json" is expected to be collected as an artifact with the following
    values:

        {
            "phase": "Name of phase",
            "jobs": [
                {"name": "Optional name",
                 "cmd": "echo 1"},
                {"cmd": "py.test --junit=junit.xml"}
            ]
        }

    For each job listed, a new generic task will be executed grouped under the
    given phase name.
    """
    # TODO(dcramer): longer term we'd rather have this create a new phase which
    # actually executes a different BuildStep (e.g. of order + 1), but at the
    # time of writing the system only supports a single build step.
    builder_cls = JenkinsCollectorBuilder

    def get_label(self):
        return 'Collect jobs from job "{0}" on Jenkins'.format(self.job_name)

    def fetch_artifact(self, artifact, **kwargs):
        if os.path.basename(artifact.data['fileName']) == self.get_builder().get_required_artifact():
            self._expand_jobs(artifact.step, artifact)
        else:
            super(JenkinsCollectorBuildStep, self).fetch_artifact(artifact, **kwargs)

    def _expand_jobs(self, step, artifact):
        builder = self.get_builder()
        artifact_data = builder.fetch_artifact(step, artifact.data)
        phase_config = artifact_data.json()

        assert phase_config['phase']
        assert phase_config['jobs']

        phase, created = get_or_create(JobPhase, where={
            'job': step.job,
            'project': step.project,
            'label': phase_config['phase'],
        }, defaults={
            'status': Status.queued,
        })

        for job_config in phase_config['jobs']:
            assert job_config['cmd']
            label = job_config.get('name') or md5(job_config['cmd']).hexdigest()
            self._expand_job(phase, label, job_config['cmd'])

    def _expand_job(self, phase, label, cmd):
        step, created = get_or_create(JobStep, where={
            'job': phase.job,
            'project': phase.project,
            'phase': phase,
            'label': label,
        }, defaults={
            'data': {
                'cmd': cmd,
                'job_name': self.job_name,
                'build_no': None,
                'expanded': True,
            },
            'status': Status.queued,
        })
        BuildStep.handle_debug_infra_failures(step, self.debug_config, 'expanded')

        builder = self.get_builder()
        builder.create_jenkins_build(step, job_name=step.data['job_name'], script=step.data['cmd'])

        sync_job_step.delay_if_needed(
            step_id=step.id.hex,
            task_id=step.id.hex,
            parent_task_id=phase.job.id.hex,
        )
        return step
