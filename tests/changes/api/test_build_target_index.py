from uuid import uuid4

from changes.constants import Result, Status
from changes.testutils import APITestCase


class BuildTargetIndexTest(APITestCase):
    def test_simple(self):
        fake_id = uuid4()

        project = self.create_project()
        build = self.create_build(project, result=Result.failed)
        job = self.create_job(build, status=Status.finished)
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase)
        target = self.create_target(
            job=job,
            jobstep=step,
            name='bar',
            result=Result.failed,
            status=Status.finished,
            duration=15,
        )
        self.create_target_message(target)
        self.create_target_message(target)
        self.create_target_message(target)
        target2 = self.create_target(
            job=job,
            jobstep=step,
            name='foo',
            result=Result.failed,
            status=Status.finished,
            duration=10,
        )

        path = '/api/0/builds/{0}/targets/'.format(fake_id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 404

        # test each sort option just to ensure it doesnt straight up fail
        path = '/api/0/builds/{0}/targets/?sort=duration'.format(build.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 2
        assert data[0]['id'] == target.id.hex
        assert len(data[0]['messages']) == 3
        assert data[1]['id'] == target2.id.hex
        assert len(data[1]['messages']) == 0

        path = '/api/0/builds/{0}/targets/?sort=name'.format(build.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 2
        assert data[0]['id'] == target.id.hex
        assert data[1]['id'] == target2.id.hex

        path = '/api/0/builds/{0}/targets/?sort=name&reverse=true'.format(build.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 2
        assert data[0]['id'] == target2.id.hex
        assert data[1]['id'] == target.id.hex

        path = '/api/0/builds/{0}/targets/?per_page='.format(build.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 2
        assert data[0]['id'] == target.id.hex
        assert data[1]['id'] == target2.id.hex

        path = '/api/0/builds/{0}/targets/?query=foo'.format(build.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == target2.id.hex

        path = '/api/0/builds/{0}/targets/?query=somethingelse'.format(build.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 0

        path = '/api/0/builds/{0}/targets/?result='.format(build.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 2

        path = '/api/0/builds/{0}/targets/?result=passed'.format(build.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 0
