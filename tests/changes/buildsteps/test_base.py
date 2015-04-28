from __future__ import absolute_import


from changes.constants import Result, Status
from changes.buildsteps.base import BuildStep
from changes.testutils import TestCase


class BuildStepTest(TestCase):
    def get_buildstep(self):
        return BuildStep()

    def test_validate_phase(self):
        project = self.create_project()
        build = self.create_build(
            project=project,
            status=Status.finished,
            result=Result.passed,
        )
        job = self.create_job(build)

        buildstep = self.get_buildstep()

        # Successful
        phase = self.create_jobphase(job, label="phase1")
        step = self.create_jobstep(
            phase,
            status=Status.finished,
            result=Result.passed,
        )
        buildstep.validate_phase(phase)
        assert phase.result == Result.passed

        # Failed
        phase2 = self.create_jobphase(job, label="phase2")
        step2 = self.create_jobstep(
            phase2,
            status=Status.finished,
            result=Result.failed,
        )
        buildstep.validate_phase(phase2)
        assert phase2.result == Result.failed

    def test_validate(self):
        project = self.create_project()
        build = self.create_build(
            project=project,
            status=Status.finished,
            result=Result.passed,
        )

        buildstep = self.get_buildstep()

        # Successful
        job = self.create_job(build)
        phase = self.create_jobphase(
            job,
            label="phase1",
            status=Status.finished,
            result=Result.passed,
        )
        buildstep.validate(job)
        assert job.result == Result.passed

        # Failed
        job2 = self.create_job(build)
        phase2 = self.create_jobphase(
            job2,
            label="phase2",
            status=Status.finished,
            result=Result.failed,
        )
        buildstep.validate(job2)
        assert job2.result == Result.failed
