from changes.api.serializer import serialize
from changes.config import db
from changes.models import ProjectOption

from changes.testutils import TestCase


class JobStepCrumblerTestCase(TestCase):
    def test_associated_snapshot_image(self):
        project = self.create_project()
        build = self.create_build(project=project)
        plan = self.create_plan(project)
        job = self.create_job(build=build)
        snapshot = self.create_snapshot(project)
        image = self.create_snapshot_image(plan=plan, snapshot=snapshot)
        self.create_option(item_id=plan.id, name='snapshot.allow', value='1')
        db.session.add(ProjectOption(project_id=project.id,
                                     name='snapshot.current',
                                     value=snapshot.id.hex))
        db.session.commit()
        self.create_job_plan(job=job, plan=plan, snapshot_id=snapshot.id)
        phase = self.create_jobphase(job)
        jobstep = self.create_jobstep(phase)

        result = serialize(jobstep)
        assert result['image']['id'] == image.id.hex
