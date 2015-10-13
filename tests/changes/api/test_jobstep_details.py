from uuid import uuid4

from changes.config import db
from changes.constants import Cause, Result, Status
from changes.models import CommandType, JobStep, ProjectOption
from changes.testutils import APITestCase


class JobStepDetailsTest(APITestCase):
    def test_invalid_id(self):
        path = '/api/0/jobsteps/{0}/'.format(uuid4().hex)

        resp = self.client.get(path)
        assert resp.status_code == 404

    def test_without_snapshot(self):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase)

        path = '/api/0/jobsteps/{0}/'.format(jobstep.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == jobstep.id.hex
        assert data['snapshot'] is None
        assert data['expectedSnapshot'] is None

    def test_without_image(self):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase)
        snapshot = self.create_snapshot(project)
        db.session.add(ProjectOption(
            project_id=project.id,
            name='snapshot.current',
            value=snapshot.id.hex,
        ))
        db.session.commit()

        path = '/api/0/jobsteps/{0}/'.format(jobstep.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == jobstep.id.hex
        assert data['snapshot'] is None
        assert data['expectedSnapshot'] is None

    def test_with_snapshot(self):
        project = self.create_project()
        build = self.create_build(project)
        plan = self.create_plan(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase)
        snapshot = self.create_snapshot(project)
        image = self.create_snapshot_image(
            plan=plan,
            snapshot=snapshot,
        )
        self.create_option(
            item_id=plan.id,
            name='snapshot.allow',
            value='1'
        )
        db.session.add(ProjectOption(
            project_id=project.id,
            name='snapshot.current',
            value=snapshot.id.hex,
        ))
        db.session.commit()

        self.create_job_plan(job, plan, snapshot.id)
        db.session.commit()

        path = '/api/0/jobsteps/{0}/'.format(jobstep.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == jobstep.id.hex
        assert data['snapshot']['id'] == image.id.hex
        assert data['expectedSnapshot'] is None

    def test_with_snapshot_disallowed(self):
        project = self.create_project()
        build = self.create_build(project)
        plan = self.create_plan(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase)
        snapshot = self.create_snapshot(project)
        image = self.create_snapshot_image(
            plan=plan,
            snapshot=snapshot,
        )
        self.create_option(
            item_id=plan.id,
            name='snapshot.allow',
            value='0'
        )
        db.session.add(ProjectOption(
            project_id=project.id,
            name='snapshot.current',
            value=snapshot.id.hex,
        ))
        db.session.commit()

        self.create_job_plan(job, plan, snapshot.id)
        db.session.commit()

        path = '/api/0/jobsteps/{0}/'.format(jobstep.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == jobstep.id.hex
        assert data['snapshot'] is None
        assert data['expectedSnapshot'] is None

    def test_with_expected_snapshot(self):
        project = self.create_project()
        build = self.create_build(project, cause=Cause.snapshot)
        plan = self.create_plan(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase)
        self.create_job_plan(job, plan)
        snapshot = self.create_snapshot(project)
        self.create_snapshot_image(
            plan=plan,
            snapshot=snapshot,
        )
        db.session.add(ProjectOption(
            project_id=project.id,
            name='snapshot.current',
            value=snapshot.id.hex,
        ))
        new_snapshot = self.create_snapshot(project)
        new_image = self.create_snapshot_image(
            plan=plan,
            snapshot=new_snapshot,
            job=job,
        )
        db.session.commit()

        path = '/api/0/jobsteps/{0}/'.format(jobstep.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == jobstep.id.hex
        assert data['snapshot'] is None
        assert data['expectedSnapshot']['id'] == new_image.id.hex


class UpdateJobStepTest(APITestCase):
    def test_invalid_id(self):
        path = '/api/0/jobsteps/{0}/'.format(uuid4().hex)

        resp = self.client.post(path)
        assert resp.status_code == 404

    def test_simple(self):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(
            jobphase, status=Status.queued, result=Result.unknown,
            date_started=None, date_finished=None)

        path = '/api/0/jobsteps/{0}/'.format(jobstep.id.hex)

        resp = self.client.post(path, data={
            'status': 'in_progress'
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == jobstep.id.hex

        jobstep = JobStep.query.get(jobstep.id)

        assert jobstep.status == Status.in_progress
        assert jobstep.result == Result.unknown
        assert jobstep.date_started is not None
        assert jobstep.date_finished is None

        resp = self.client.post(path, data={
            'status': 'queued'
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == jobstep.id.hex

        jobstep = JobStep.query.get(jobstep.id)

        assert jobstep.status == Status.queued
        assert jobstep.result == Result.unknown
        assert jobstep.date_started is None
        assert jobstep.date_finished is None

        resp = self.client.post(path, data={
            'status': 'finished',
            'result': 'passed'
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == jobstep.id.hex

        jobstep = JobStep.query.get(jobstep.id)

        assert jobstep.status == Status.finished
        assert jobstep.result == Result.passed
        assert jobstep.date_started is not None
        assert jobstep.date_finished is not None

        resp = self.client.post(path, data={
            'node': 'foo',
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == jobstep.id.hex

        db.session.expire(jobstep)
        jobstep = JobStep.query.get(jobstep.id)
        assert jobstep.node.label == 'foo'

        resp = self.client.post(path, data={
            'node': 'bar',
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == jobstep.id.hex

        db.session.expire(jobstep)
        jobstep = JobStep.query.get(jobstep.id)
        assert jobstep.node.label == 'bar'

    def test_missing_expected_tests_collector(self):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(
            jobphase, status=Status.queued, result=Result.unknown,
            date_started=None, date_finished=None)
        self.create_command(
            jobstep=jobstep,
            type=CommandType.collect_tests,
            return_code=0,
            status=Status.finished,
        )

        path = '/api/0/jobsteps/{0}/'.format(jobstep.id.hex)

        resp = self.client.post(path, data={
            'status': 'finished',
            'result': 'passed'
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == jobstep.id.hex

        jobstep = JobStep.query.get(jobstep.id)

        assert jobstep.status == Status.finished
        assert jobstep.result == Result.failed
        assert jobstep.date_started is not None
        assert jobstep.date_finished is not None

    def test_failed_command(self):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(
            jobphase, status=Status.queued, result=Result.unknown,
            date_started=None, date_finished=None)
        self.create_command(
            jobstep=jobstep,
            type=CommandType.collect_tests,
            return_code=1,
            status=Status.finished,
        )
        path = '/api/0/jobsteps/{0}/'.format(jobstep.id.hex)

        resp = self.client.post(path, data={
            'status': 'finished',
            'result': 'passed'
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == jobstep.id.hex

        jobstep = JobStep.query.get(jobstep.id)

        assert jobstep.status == Status.finished
        assert jobstep.result == Result.failed
        assert jobstep.date_started is not None
        assert jobstep.date_finished is not None

    def test_unfinished_command(self):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(
            jobphase, status=Status.queued, result=Result.unknown,
            date_started=None, date_finished=None)
        self.create_command(
            jobstep=jobstep,
            type=CommandType.collect_tests,
            return_code=0,
            status=Status.unknown,
        )
        path = '/api/0/jobsteps/{0}/'.format(jobstep.id.hex)

        resp = self.client.post(path, data={
            'status': 'finished',
            'result': 'passed'
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == jobstep.id.hex

        jobstep = JobStep.query.get(jobstep.id)

        assert jobstep.status == Status.finished
        assert jobstep.result == Result.failed
        assert jobstep.date_started is not None
        assert jobstep.date_finished is not None

    def test_dependent_snapshot(self):
        project = self.create_project()
        build = self.create_build(project)
        plan_1 = self.create_plan(project)
        plan_2 = self.create_plan(project)
        plan_1.snapshot_plan_id = plan_2.id
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase)
        snapshot = self.create_snapshot(project)
        image_1 = self.create_snapshot_image(snapshot, plan_1)
        image_2 = self.create_snapshot_image(snapshot, plan_2)
        db.session.add(ProjectOption(
            project_id=project.id,
            name='snapshot.current',
            value=snapshot.id.hex,
        ))
        db.session.commit()

        self.create_job_plan(job, plan_1, snapshot.id)
        db.session.commit()

        path = '/api/0/jobsteps/{0}/'.format(jobstep.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['snapshot']['id'] == image_2.id.hex

    def test_multiple_jobsteps(self):
        project = self.create_project()
        build = self.create_build(project)
        plan_1 = self.create_plan(project)
        plan_2 = self.create_plan(project)
        plan_1.snapshot_plan_id = plan_2.id
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase)
        snapshot = self.create_snapshot(project)
        image_1 = self.create_snapshot_image(snapshot, plan_1)
        image_2 = self.create_snapshot_image(snapshot, plan_2)
        db.session.add(ProjectOption(
            project_id=project.id,
            name='snapshot.current',
            value=snapshot.id.hex,
        ))
        db.session.commit()

        self.create_job_plan(job, plan_1, snapshot.id)
        db.session.commit()

        path = '/api/0/jobsteps/{0}/'.format(jobstep.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['snapshot']['id'] == image_2.id.hex
