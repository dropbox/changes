from changes.constants import Cause
from changes.models import Build
from changes.testutils import APITestCase


class BuildRetryTest(APITestCase):
    def test_simple(self):
        change = self.create_change(self.project)
        build = self.create_build(self.project, change=change)

        path = '/api/0/builds/{0}/retry/'.format(build.id.hex)
        resp = self.client.post(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['build']['id']
        assert data['build']['link']
        new_build = Build.query.get(data['build']['id'])
        assert new_build.id != build.id
        assert new_build.change == change
        assert new_build.project == self.project
        assert new_build.cause == Cause.retry
        assert new_build.parent_id == build.id
        assert new_build.revision_sha == build.revision_sha
        assert new_build.author_id == build.author_id
        assert new_build.label == build.label
        assert new_build.message == build.message
        assert new_build.target == build.target
