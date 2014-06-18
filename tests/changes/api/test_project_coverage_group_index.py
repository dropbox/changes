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

        path = '/api/0/projects/{0}/coveragegroups/'.format(fake_project_id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 404

        path = '/api/0/projects/{0}/coveragegroups/'.format(project.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data['groups']) == 2
        assert data['groups'][0]['filename'] == 'blah/blah.py'
        assert data['groups'][0]['path'] == 'blah/blah.py'
        assert data['groups'][0]['numFiles'] == 1
        assert data['groups'][0]['totalLinesCovered'] == 6
        assert data['groups'][0]['totalLinesUncovered'] == 23
        assert data['groups'][1]['filename'] == 'foo'
        assert data['groups'][1]['path'] == 'foo'
        assert data['groups'][1]['numFiles'] == 2
        assert data['groups'][1]['totalLinesCovered'] == 5
        assert data['groups'][1]['totalLinesUncovered'] == 12
        assert len(data['trail']) == 0

        path = '/api/0/projects/{0}/coveragegroups/?parent=foo'.format(project.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data['groups']) == 2
        assert data['groups'][0]['filename'] == 'bar.py'
        assert data['groups'][0]['path'] == 'foo/bar.py'
        assert data['groups'][0]['numFiles'] == 1
        assert data['groups'][0]['totalLinesCovered'] == 5
        assert data['groups'][0]['totalLinesUncovered'] == 7
        assert data['groups'][1]['filename'] == 'baz.py'
        assert data['groups'][1]['path'] == 'foo/baz.py'
        assert data['groups'][1]['numFiles'] == 1
        assert data['groups'][1]['totalLinesCovered'] == 0
        assert data['groups'][1]['totalLinesUncovered'] == 5
        assert len(data['trail']) == 1
        assert data['trail'][0] == {
            'name': 'foo',
            'path': 'foo',
        }
