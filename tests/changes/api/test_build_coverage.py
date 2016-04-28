from uuid import uuid4

from changes.config import db
from changes.constants import Result, Status
from changes.models.filecoverage import FileCoverage
from changes.testutils import APITestCase


class BuildCoverageTest(APITestCase):
    def test_error(self):
        fake_build_id = uuid4()

        path = '/api/0/builds/{0}/coverage/'.format(fake_build_id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 404

    def test_merging(self):
        project = self.create_project()
        build = self.create_build(
            project, status=Status.finished, result=Result.passed)
        # One build with two jobs.
        job1 = self.create_job(build)
        phase1 = self.create_jobphase(job1)
        step1 = self.create_jobstep(phase1)
        job2 = self.create_job(build)
        phase2 = self.create_jobphase(job2)
        step2 = self.create_jobstep(phase2)

        # Two jobs contribute to coverage for foo.py.
        db.session.add(FileCoverage(
            step_id=step1.id,
            job_id=job1.id,
            project_id=project.id,
            lines_covered=1,
            lines_uncovered=1,
            filename="foo.py",
            data="NNUC",
        ))
        db.session.add(FileCoverage(
            step_id=step1.id,
            job_id=job1.id,
            project_id=project.id,
            lines_covered=1,
            lines_uncovered=1,
            filename="bar.py",
            data="CNNU",
        ))
        db.session.add(FileCoverage(
            step_id=step2.id,
            job_id=job2.id,
            project_id=project.id,
            lines_covered=1,
            lines_uncovered=1,
            filename="foo.py",
            data="NUCN",
        ))
        db.session.commit()

        path = '/api/0/builds/{0}/coverage/'.format(build.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data == {
            "foo.py": "NUCC",  # Merged.
            "bar.py": "CNNU",
            }
