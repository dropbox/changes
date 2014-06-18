from uuid import uuid4

from changes.config import db
from changes.constants import Result, Status
from changes.models import TestCase
from changes.testutils import APITestCase


class BuildTestIndexTest(APITestCase):
    def test_simple(self):
        fake_id = uuid4()

        build = self.create_build(self.project, result=Result.failed)
        job = self.create_job(build, status=Status.finished)

        test = TestCase(
            job=job,
            project=self.project,
            name='foo',
            name_sha='a' * 40,
        )
        db.session.add(test)

        path = '/api/0/builds/{0}/tests/'.format(fake_id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 404

        # test each sort option just to ensure it doesnt straight up fail
        path = '/api/0/builds/{0}/tests/?sort=duration'.format(build.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == test.id.hex

        path = '/api/0/builds/{0}/tests/?sort=name'.format(build.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == test.id.hex

        path = '/api/0/builds/{0}/tests/?sort=retries'.format(build.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == test.id.hex

        path = '/api/0/builds/{0}/tests/?per_page='.format(build.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == test.id.hex

        path = '/api/0/builds/{0}/tests/?query=foo'.format(build.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == test.id.hex

        path = '/api/0/builds/{0}/tests/?query=bar'.format(build.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 0

        path = '/api/0/builds/{0}/tests/?result='.format(build.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1

        path = '/api/0/builds/{0}/tests/?result=passed'.format(build.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 0
