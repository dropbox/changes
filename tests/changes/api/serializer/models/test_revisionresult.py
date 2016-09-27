from changes.api.serializer import serialize
from changes.testutils.cases import TestCase


class RevisionResultCrumblerTestCase(TestCase):

    def test_simple(self):
        build = self.create_build(self.create_project())
        revision_result = self.create_revision_result(build=build, revision_sha=build.source.revision_sha, project_id=build.project_id)

        data = serialize(revision_result)
        assert data['id'] == revision_result.id.hex
        assert data['revisionSha'] == revision_result.revision_sha
        assert data['build']['id'] == build.id.hex
        assert data['result']['id'] == 'unknown'

    def test_no_build(self):
        project = self.create_project()
        revision_result = self.create_revision_result(revision_sha='a' * 40, project_id=project.id)

        data = serialize(revision_result)
        assert data['id'] == revision_result.id.hex
        assert data['revisionSha'] == 'a' * 40
        assert data['build'] is None
        assert data['result']['id'] == 'unknown'
