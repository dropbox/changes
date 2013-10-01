from cStringIO import StringIO

from changes.models import Build, Patch
from changes.testutils import APITestCase


SAMPLE_DIFF = """diff --git a/README.rst b/README.rst
index 2ef2938..ed80350 100644
--- a/README.rst
+++ b/README.rst
@@ -1,5 +1,5 @@
 Setup
------
+====="""


class BuildListTest(APITestCase):
    def test_simple(self):
        change = self.create_change(self.project)
        build = self.create_build(self.project, change=change)
        self.create_build(self.project2)

        path = '/api/0/changes/{0}/builds/'.format(change.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data['builds']) == 1
        assert data['builds'][0]['id'] == build.id.hex


class BuildCreateTest(APITestCase):
    def test_simple(self):
        change = self.create_change(self.project)
        path = '/api/0/changes/{0}/builds/'.format(change.id.hex)
        resp = self.client.post(path, data={
            'sha': 'a' * 40,
            'author': 'David Cramer <dcramer@example.com>',
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['build']['id']
        build = Build.query.get(data['build']['id'])
        assert build.change == change
        assert build.project == self.project
        assert build.parent_revision_sha == 'a' * 40
        assert build.author.name == 'David Cramer'
        assert build.author.email == 'dcramer@example.com'
        self.mock_backend.create_build.assert_called_once_with(
            build)

    def test_with_patch(self):
        change = self.create_change(self.project)
        path = '/api/0/changes/{0}/builds/'.format(change.id.hex)
        resp = self.client.post(path, data={
            'sha': 'a' * 40,
            'author': 'David Cramer <dcramer@example.com>',
            'patch': (StringIO(SAMPLE_DIFF), 'foo.diff'),
            'patch_label': 'D1234',
            'patch_url': 'http://phabricator.example.com/D1234',
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['build']['id']
        build = Build.query.get(data['build']['id'])
        self.mock_backend.create_build.assert_called_once_with(
            build)
        assert build.patch_id is not None
        patch = Patch.query.get(build.patch_id)
        assert patch.diff == SAMPLE_DIFF
        assert patch.label == 'D1234'
        assert patch.url == 'http://phabricator.example.com/D1234'
        assert patch.parent_revision_sha == 'a' * 40
