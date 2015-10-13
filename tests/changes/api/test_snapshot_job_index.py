import uuid

from changes.config import db
from changes.testutils import APITestCase


class SnapshotJobIndexTest(APITestCase):
    def test_get_jobs_by_snapshot(self):
        project = self.create_project()
        plan = self.create_plan(project)
        self.create_option(item_id=plan.id, name='snapshot.allow', value='1')

        # Create snapshot
        snapshot = self.create_snapshot(project)
        snapshot_image = self.create_snapshot_image(snapshot, plan)
        option = self.create_project_option(project, 'snapshot.current', snapshot.id.hex)
        db.session.commit()

        expected_jobs = []
        for i in range(2):
            build = self.create_build(project)
            job = self.create_job(build)
            expected_jobs.append(job)
            jobplan = self.create_job_plan(job, plan, snapshot.id)
            assert jobplan.snapshot_image_id == snapshot_image.id
        db.session.commit()

        # Create a new snapshot
        snapshot_2 = self.create_snapshot(project)
        snapshot_image_2 = self.create_snapshot_image(snapshot_2, plan)
        option.value = snapshot_2.id.hex
        db.session.add(option)
        db.session.commit()

        for i in range(2):
            build = self.create_build(project)
            job = self.create_job(build)
            jobplan = self.create_job_plan(job, plan, snapshot_2.id)
            assert jobplan.snapshot_image_id == snapshot_image_2.id
        db.session.commit()

        # Query should only return jobs from the first snapshot
        path = '/api/0/snapshots/{0}/jobs/'.format(snapshot.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == len(expected_jobs)
        assert set([x['id'] for x in data]) == set([j.id.hex for j in expected_jobs])

    def test_fake_snapshot(self):
        path = '/api/0/snapshots/{0}/jobs/'.format(uuid.uuid4())
        resp = self.client.get(path)
        assert resp.status_code == 404
