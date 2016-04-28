from mock import patch
from uuid import uuid4

from changes.api.project_snapshot_index import get_snapshottable_plans
from changes.buildsteps.dummy import DummyBuildStep
from changes.config import db
from changes.constants import Status, Cause
from changes.models.build import BuildPriority
from changes.models.jobplan import JobPlan
from changes.models.snapshot import Snapshot, SnapshotImage, SnapshotStatus
from changes.testutils import APITestCase


class SnapshottableBuildStep(DummyBuildStep):
    def can_snapshot(self):
        return True


class GetSnapshottablePlansTest(APITestCase):
    def test_missing_buildstep(self):
        project = self.create_project()
        plan = self.create_plan(project)
        self.create_option(item_id=plan.id, name='snapshot.allow', value='1')

        result = get_snapshottable_plans(project)
        assert result == []

    @patch('changes.models.step.Step.get_implementation')
    def test_dependent_snapshot_plan(self, mock_get_implementation):
        project = self.create_project()
        plan_1 = self.create_plan(project)
        plan_2 = self.create_plan(project)
        plan_1.snapshot_plan_id = plan_2.id

        mock_get_implementation.return_value = SnapshottableBuildStep()
        self.create_option(item_id=plan_1.id, name='snapshot.allow', value='1')
        self.create_step(plan_1)

        result = get_snapshottable_plans(project)
        assert result == []

    @patch('changes.models.step.Step.get_implementation')
    def test_unsnapshottable_buildstep(self, mock_get_implementation):
        project = self.create_project()
        plan = self.create_plan(project)
        self.create_option(item_id=plan.id, name='snapshot.allow', value='1')
        self.create_step(plan)

        mock_get_implementation.return_value = DummyBuildStep()

        result = get_snapshottable_plans(project)
        assert result == []

    @patch('changes.models.step.Step.get_implementation')
    def test_disabled_plan(self, mock_get_implementation):
        project = self.create_project()
        plan = self.create_plan(project)
        self.create_option(item_id=plan.id, name='snapshot.allow', value='0')
        self.create_step(plan)

        mock_get_implementation.return_value = SnapshottableBuildStep()

        result = get_snapshottable_plans(project)
        assert result == []

    @patch('changes.models.step.Step.get_implementation')
    def test_valid_plan(self, mock_get_implementation):
        project = self.create_project()
        plan = self.create_plan(project)
        self.create_step(plan)
        self.create_option(item_id=plan.id, name='snapshot.allow', value='1')

        mock_get_implementation.return_value = SnapshottableBuildStep()

        result = get_snapshottable_plans(project)
        assert result == [plan]


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

    @patch('changes.api.project_snapshot_index.get_snapshottable_plans')
    @patch('changes.jobs.create_job.create_job.delay')
    @patch('changes.jobs.sync_build.sync_build.delay')
    def test_simple(self, mock_sync_build, mock_create_job,
                    mock_get_snapshottable_plans):
        project = self.create_project()

        path = '/api/0/projects/{0}/snapshots/'.format(project.id.hex)

        mock_get_snapshottable_plans.return_value = []

        # missing plan
        resp = self.client.post(path, data={
            'sha': 'a' * 40,
        })
        assert resp.status_code == 400

        plan_1 = self.create_plan(project, label='a')

        plan_2 = self.create_plan(project, label='b')

        mock_get_snapshottable_plans.reset_mock()
        mock_get_snapshottable_plans.return_value = [plan_1, plan_2]

        db.session.commit()

        # missing sha
        resp = self.client.post(path)
        assert resp.status_code == 400

        revision_sha = 'c' * 40
        # A patch source based on same revision. Patch sources should not be used.
        patch = self.create_patch()
        self.create_source(project, revision_sha=revision_sha, patch_id=patch.id)

        # valid params
        resp = self.client.post(path, data={
            'sha': revision_sha,
        })
        assert resp.status_code == 200
        mock_get_snapshottable_plans.assert_called_once_with(project)
        data = self.unserialize(resp)

        snapshot = Snapshot.query.get(data['id'])
        assert snapshot.source.revision_sha == revision_sha
        assert snapshot.source.patch_id is None
        assert snapshot.project_id == project.id
        assert snapshot.status == SnapshotStatus.pending

        build = snapshot.build
        assert build.cause == Cause.snapshot
        assert build.status == Status.queued
        assert build.priority == BuildPriority.high
        assert build.tags == ['snapshot']

        images = sorted(SnapshotImage.query.filter(
            SnapshotImage.snapshot_id == snapshot.id,
        ), key=lambda x: x.plan.label)

        assert len(images) == 2
        assert images[0].plan_id == plan_1.id
        assert images[0].job_id
        assert images[1].plan_id == plan_2.id
        assert images[1].job_id
        assert images[0].job_id != images[1].job_id

        # Verify that snapshot builds don't use snapshots
        jobplans = [JobPlan.query.filter(
            JobPlan.plan_id == image.plan.id,
            JobPlan.job_id == image.job.id
        ).scalar() for image in [images[0], images[1]]]
        for jobplan in jobplans:
            assert jobplan.snapshot_image_id is None

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
