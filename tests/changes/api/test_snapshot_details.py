from random import randint

from changes.testutils import APITestCase


class SnapshotDetailsTest(APITestCase):
    def test_simple(self):
        project = self.create_project()
        snapshot = self.create_snapshot(project, url="foo.com")

        path = '/api/0/snapshots/{0}/'.format(snapshot.id)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == snapshot.id.hex
        assert data['url'] == snapshot.url
        assert data['project_id'] == project.id.hex
        assert data['build_id'] is None


class UpdateSnapshotTest(APITestCase):
    def test_simple(self):
        project = self.create_project()
        snapshot = self.create_snapshot(project)

        path = '/api/0/snapshots/{0}/'.format(snapshot.id.hex)

        for status in ('active', 'failed', 'invalidated'):
            url = "foo{0}.com".format(randint(0, 100))
            resp = self.client.post(path, data={
                'status': status,
                'url': url,
            })

            assert resp.status_code == 200
            data = self.unserialize(resp)
            assert data['id'] == snapshot.id.hex
            assert data['url'] == url
            assert data['project_id'] == project.id.hex

        resp = self.client.post(path, data={
            'status': 'invalid_status',
            'url': url,
        })

        assert resp.status_code == 400
