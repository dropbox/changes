from mock import patch
from uuid import uuid4

from changes.config import db
from changes.constants import Status, Cause
from changes.models import Snapshot, SnapshotImage, SnapshotStatus
from changes.testutils import APITestCase


class ProjectSnapshotListTest(APITestCase):
    def test_invalid_project_id(self):
        fake_project_id = uuid4()

        path = '/api/0/projects/{0}/snapshots/'.format(fake_project_id.hex)

        # invalid project id
        resp = self.client.get(path)
        assert resp.status_code == 404

    def test_simple(self):
        project_1 = self.create_project()
        self.create_snapshot(project_1)

        project_2 = self.create_project()
        snapshot = self.create_snapshot(project_2)

        path = '/api/0/projects/{0}/snapshots/'.format(project_2.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == snapshot.id.hex


class CreateProjectSnapshotTest(APITestCase):
    def test_invalid_project_id(self):
        fake_project_id = uuid4()

        path = '/api/0/projects/{0}/snapshots/'.format(fake_project_id.hex)

        # invalid project id
        resp = self.client.post(path, data={
            'sha': 'a' * 40,
        })
        assert resp.status_code == 404

    @patch('changes.jobs.create_job.create_job.delay')
    @patch('changes.jobs.sync_build.sync_build.delay')
    def test_simple(self, mock_sync_build, mock_create_job):
        project = self.create_project()

        path = '/api/0/projects/{0}/snapshots/'.format(project.id.hex)

        # missing plan
        resp = self.client.post(path, data={
            'sha': 'a' * 40,
        })
        assert resp.status_code == 400

        plan_1 = self.create_plan(label='a')
        plan_1.projects.append(project)

        plan_2 = self.create_plan(label='b')
        plan_2.projects.append(project)

        db.session.commit()

        # missing sha
        resp = self.client.post(path)
        assert resp.status_code == 400

        resp = self.client.post(path, data={
            'sha': 'a' * 40,
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)

        snapshot = Snapshot.query.get(data['id'])
        assert snapshot.source.revision_sha == 'a' * 40
        assert snapshot.project_id == project.id
        assert snapshot.status == SnapshotStatus.pending

        build = snapshot.build
        assert build.cause == Cause.snapshot
        assert build.status == Status.queued

        images = sorted(SnapshotImage.query.filter(
            SnapshotImage.snapshot_id == snapshot.id,
        ), key=lambda x: x.plan.label)

        assert len(images) == 2
        assert images[0].plan_id == plan_1.id
        assert images[0].job_id
        assert images[1].plan_id == plan_2.id
        assert images[1].job_id
        assert images[0].job_id != images[1].job_id

        assert len(mock_create_job.mock_calls) == 2
        for image in images:
            mock_create_job.assert_any_call(
                job_id=image.job_id.hex,
                task_id=image.job_id.hex,
                parent_task_id=build.id.hex,
            )

        mock_sync_build.assert_called_once_with(
            build_id=build.id.hex,
            task_id=build.id.hex,
        )
