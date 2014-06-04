from uuid import uuid4

from changes.config import db
from changes.constants import Result, Status
from changes.models import FileCoverage
from changes.testutils import APITestCase


class ProjectCoverageGroupIndexTest(APITestCase):
    def test_simple(self):
        fake_project_id = uuid4()

        build = self.create_build(self.project)
        self.create_job(build)

        project = self.create_project()
        build = self.create_build(
            project, status=Status.finished, result=Result.passed)
        job = self.create_job(build)
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase)

        db.session.add(FileCoverage(
            step_id=step.id,
            job_id=job.id,
            project_id=project.id,
            lines_covered=5,
            lines_uncovered=7,
            filename="foo/bar.py",
        ))
        db.session.add(FileCoverage(
            step_id=step.id,
            job_id=job.id,
            project_id=project.id,
            lines_covered=0,
            lines_uncovered=5,
            filename="foo/baz.py",
        ))
        db.session.add(FileCoverage(
            step_id=step.id,
            job_id=job.id,
            project_id=project.id,
            lines_covered=6,
            lines_uncovered=23,
            filename="blah/blah.py",
        ))
        db.session.commit()

        path = '/api/0/projects/{0}/coverage/'.format(fake_project_id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 404

        path = '/api/0/projects/{0}/coverage/'.format(project.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 3
        assert data[0] == {
            'filename': 'blah/blah.py',
            'linesCovered': 6,
            'linesUncovered': 23,
        }
