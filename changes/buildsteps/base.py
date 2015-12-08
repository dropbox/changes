from __future__ import absolute_import

from datetime import datetime
from collections import namedtuple

from changes.config import db
from changes.constants import Result, Status
from changes.models.jobstep import JobStep
from changes.utils.agg import aggregate_result


LXCConfig = namedtuple('LXCConfig', ['compression',
                                     'release',
                                     'prelaunch',
                                     'postlaunch',
                                     's3_bucket'])


class BuildStep(object):
    def can_snapshot(self):
        return False

    def get_label(self):
        raise NotImplementedError

    def get_resource_limits(self):
        """Return the resource limits that should be applied to individual executions.
        The return value is expected to be a dict like:
           {'cpus': 4, 'memory': 8000}
        with 'cpus' and 'memory' indicating the number of CPUs and megabytes of memory needed
        respectively. Both fields are optional.
        Specifying these values don't guarantee you'll get them (or that you won't get more),
        but it will be taken into account when scheduling jobs, and steps with lower limits
        may be scheduled sooner.
        """
        return {}

    def get_lxc_config(self, jobstep):
        """
        Get the LXC configuration, if the LXC adapter should be used.
        Args:
            jobstep (JobStep): The JobStep to get the LXC config for.

        Returns:
            LXCConfig: The config to use for this jobstep, or None.
        """
        return None

    def get_test_stats_from(self):
        """
        Returns the project slug that test statistics should be retrieved from,
        or None to use the current project.
        """
        return None

    def execute(self, job):
        """
        Given a new job, execute it (either sync or async), and report the
        results or yield to an update step.
        """
        raise NotImplementedError

    def create_replacement_jobstep(self, step):
        """Attempt to create a replacement of the given jobstep.

        Returns new jobstep if successful, None otherwise."""
        return None

    def update(self, job):
        raise NotImplementedError

    def update_step(self, step):
        raise NotImplementedError

    def validate(self, job):
        """Called when a job is ready to be finished.

        This is responsible for setting the job's final result. The base
        implementation simply aggregates the phase results.

        Args:
            job (Job): The job being finished.
        Returns:
            None
        """
        # TODO(josiah): ideally, we could record a FailureReason.
        # Currently FailureReason must be per-step.

        job.result = aggregate_result((p.result for p in job.phases))

    def validate_phase(self, phase):
        """Called when a job phase is ready to be finished.

        This is responsible for setting the phases's final result. The base
        implementation simply aggregates the jobstep results.

        Args:
            phase (JobPhase): The phase being finished.
        Returns:
            None
        """
        # TODO(josiah): ideally, we could record a FailureReason.
        # Currently FailureReason must be per-step.

        phase.result = aggregate_result((s.result for s in phase.current_steps))

    # There's no finish_step because steps are only marked as finished/passed
    # by update().

    def cancel(self, job):
        # XXX: this makes the assumption that sync_job will take care of
        # propagating the remainder of the metadata
        active_steps = JobStep.query.filter(
            JobStep.job == job,
            JobStep.status != Status.finished,
        )
        for step in active_steps:
            self.cancel_step(step)

            step.status = Status.finished
            step.result = Result.aborted
            step.date_finished = datetime.utcnow()
            db.session.add(step)

        db.session.flush()

    def cancel_step(self, step):
        raise NotImplementedError

    def fetch_artifact(self, artifact):
        raise NotImplementedError

    def create_expanded_jobstep(self, jobstep, new_jobphase, future_jobstep):
        raise NotImplementedError

    def get_allocation_command(self, jobstep):
        raise NotImplementedError

    def get_artifact_manager(self, jobstep):
        """
        Return an artifacts.manager.Manager object for the given jobstep.

        This manager should be created with all artifact handlers that apply.
        For instance, in a collection JobStep, you might wish to have only a
        handler for a collection artifact, whereas in JobSteps that run tests,
        you may wish to have handlers for test result files, coverage, etc.

        Args:
            jobstep: The JobStep in question.
        """
        raise NotImplementedError

    def prefer_artifactstore(self):
        """
        Return true if we should prefer the artifact store artifacts over
        those collected by Mesos/Jenkins.
        """
        return False

    def verify_final_artifacts(self, jobstep, artifacts):
        """
        Called when a jobstep is finished but we haven't yet synced its artifacts.
        Used to do any verification we might want, for instance checking for
        required artifacts.
        """

    @staticmethod
    def handle_debug_infra_failures(jobstep, debug_config, phase_type):
        """
        Uses the infra_failures debug_config to determine whether a JobStep
        should simulate an infra failure, and sets the JobStep's data field
        accordingly. (changes-client will then report an infra failure.)

        Args:
            jobstep: The JobStep in question.
            debug_config: The debug_config for this BuildStep.
            phase_type: The phase this JobStep is in. Either 'primary' or 'expanded'
        """
        infra_failures = debug_config.get('infra_failures', {})
        if phase_type in infra_failures:
            percent = jobstep.id.int % 100
            jobstep.data['debugForceInfraFailure'] = percent < infra_failures[phase_type] * 100
            db.session.add(jobstep)
