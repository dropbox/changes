from changes.config import db
from changes.constants import Result, Status
from changes.models import JobStep, ProjectOption
from changes.testutils import APITestCase


class JobStepDetailsTest(APITestCase):
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

    def test_with_snapshot(self):
        project = self.create_project()
        build = self.create_build(project)
        plan = self.create_plan()
        plan.projects.append(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase)
        snapshot = self.create_snapshot(project)
        image = self.create_snapshot_image(
            plan=plan,
            snapshot=snapshot,
            job=job,
        )
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
        assert data['snapshot']['id'] == image.id.hex


class UpdateJobStepTest(APITestCase):
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
