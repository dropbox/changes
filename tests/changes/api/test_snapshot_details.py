from random import randint

from changes.config import db
from changes.models import ProjectOption
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
    def setUp(self):
        super(UpdateSnapshotTest, self).setUp()
        self.project = self.create_project()
        self.snapshot = self.create_snapshot(self.project)
        self.path = '/api/0/snapshots/{0}/'.format(self.snapshot.id.hex)

    def test_simple(self):
        for status in ('active', 'failed', 'invalidated'):
            url = "foo{0}.com".format(randint(0, 100))
            resp = self.client.post(self.path, data={
                'status': status,
                'url': url,
            })

            assert resp.status_code == 200
            data = self.unserialize(resp)
            assert data['id'] == self.snapshot.id.hex
            assert data['url'] == url
            assert data['project_id'] == self.project.id.hex

    def test_invalid_status(self):
        resp = self.client.post(self.path, data={
            'status': 'invalid_status',
            'url': "foo",
        })
        assert resp.status_code == 400

    def test_empty_url_active(self):
        resp = self.client.post(self.path, data={
            'status': 'active',
            'url': None,
        })
        assert resp.status_code == 400

    def test_set_current(self):
        for status in ('failed', 'invalidated', 'active'):
            resp = self.client.post(self.path, data={
                'status': status,
                'url': 'foo',
                'set_current': True,
            })

            options = dict(db.session.query(
                ProjectOption.name, ProjectOption.value
            ).filter(
                ProjectOption.project == self.project,
            ))

            if status == 'active':
                assert resp.status_code == 200
                assert options.get('snapshot.current') == self.snapshot.id.hex
            else:
                assert resp.status_code == 400
                assert options.get('snapshot.current') != self.snapshot.id.hex
