from changes.testutils import APITestCase


class ProjectSourceBuildIndexTest(APITestCase):
    def test_simple(self):
        project = self.create_project()
        source = self.create_source(project)
        build1 = self.create_build(project, source=source)
        build2 = self.create_build(project, source=source)
        path = '/api/0/projects/{0}/sources/{1}/builds/'.format(
            project.id.hex, source.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 2
        assert data[0]['id'] == build2.id.hex
        assert data[1]['id'] == build1.id.hex
