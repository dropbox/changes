from datetime import datetime
from uuid import uuid4

from changes.config import db
from changes.constants import Result, Status
from changes.models.jobphase import JobPhase
from changes.models.jobstep import JobStep
from changes.models.log import LogSource
from changes.testutils import APITestCase


class JobPhaseIndexTest(APITestCase):
    def test_invalid_job_id(self):
        path = '/api/0/jobs/{0}/phases/'.format(uuid4().hex)

        resp = self.client.get(path)
        assert resp.status_code == 404

    def test_simple(self):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)

        phase_1 = JobPhase(
            job_id=job.id,
            project_id=job.project_id,
            label='Setup',
            status=Status.finished,
            result=Result.passed,
            date_created=datetime(2013, 9, 19, 22, 15, 22),
            date_started=datetime(2013, 9, 19, 22, 15, 23),
            date_finished=datetime(2013, 9, 19, 22, 15, 25),
        )
        db.session.add(phase_1)

        step_1 = JobStep(
            job_id=job.id,
            phase_id=phase_1.id,
            project_id=job.project_id,
            label='ci/setup',
            status=Status.finished,
            result=Result.passed,
            date_created=datetime(2013, 9, 19, 22, 15, 22),
            date_started=datetime(2013, 9, 19, 22, 15, 23),
            date_finished=datetime(2013, 9, 19, 22, 15, 25),
        )
        db.session.add(step_1)

        phase_2 = JobPhase(
            job_id=job.id,
            project_id=job.project_id,
            label='Test',
            status=Status.finished,
            result=Result.failed,
            date_created=datetime(2013, 9, 19, 22, 15, 23),
            date_started=datetime(2013, 9, 19, 22, 15, 24),
            date_finished=datetime(2013, 9, 19, 22, 15, 26),
        )
        db.session.add(phase_2)

        step_2_a = JobStep(
            job_id=job.id,
            phase_id=phase_2.id,
            project_id=job.project_id,
            label='test_foo.py',
            status=Status.finished,
            result=Result.passed,
            date_created=datetime(2013, 9, 19, 22, 15, 23),
            date_started=datetime(2013, 9, 19, 22, 15, 23),
            date_finished=datetime(2013, 9, 19, 22, 15, 25),
        )
        db.session.add(step_2_a)

        step_2_b = JobStep(
            job_id=job.id,
            phase_id=phase_2.id,
            project_id=job.project_id,
            label='test_bar.py',
            status=Status.finished,
            result=Result.failed,
            date_created=datetime(2013, 9, 19, 22, 15, 24),
            date_started=datetime(2013, 9, 19, 22, 15, 24),
            date_finished=datetime(2013, 9, 19, 22, 15, 26),
        )
        db.session.add(step_2_b)
        db.session.commit()

        logsource_1 = LogSource(
            job_id=job.id,
            step_id=step_1.id,
            project_id=job.project_id,
            name='test_bar.py',
            date_created=datetime(2013, 9, 19, 22, 15, 24),
        )
        db.session.add(logsource_1)
        db.session.commit()

        path = '/api/0/jobs/{0}/phases/'.format(job.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 2
        assert data[0]['id'] == phase_1.id.hex
        assert len(data[0]['steps']) == 1
        assert data[0]['steps'][0]['id'] == step_1.id.hex
        assert len(data[0]['steps'][0]['logSources']) == 1
        assert data[0]['steps'][0]['logSources'][0]['id'] == logsource_1.id.hex
        assert data[1]['id'] == phase_2.id.hex
        assert len(data[1]['steps']) == 2
        assert data[1]['steps'][0]['id'] == step_2_a.id.hex
        assert len(data[1]['steps'][0]['logSources']) == 0
        assert data[1]['steps'][1]['id'] == step_2_b.id.hex
        assert len(data[1]['steps'][1]['logSources']) == 0
