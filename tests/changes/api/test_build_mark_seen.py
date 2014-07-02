from changes.models import BuildSeen
from changes.testutils import APITestCase


class BuildMarkSeenTest(APITestCase):
    def test_simple(self):
        project = self.create_project()
        build = self.create_build(project=project)

        self.login_default()

        path = '/api/0/builds/{0}/mark_seen/'.format(build.id.hex)
        resp = self.client.post(path)

        assert resp.status_code == 200

        buildseen = BuildSeen.query.filter(
            BuildSeen.user_id == self.default_user.id,
            BuildSeen.build_id == build.id,
        ).first()

        assert buildseen
