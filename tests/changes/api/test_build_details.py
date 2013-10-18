from changes.testutils import APITestCase


class BuildDetailsTest(APITestCase):
    def test_simple(self):
        change = self.create_change(self.project)
        build = self.create_build(self.project, change=change)

        path = '/api/0/builds/{1}/'.format(
            change.id.hex, build.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['build']['id'] == build.id.hex
