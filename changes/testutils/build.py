class CreateBuildsMixin(object):
    """
    Mixin for creating and validating builds. Must be used together with
    APITestCase.
    """

    def create_repo_with_projects(self, count):
        # Create a repository with the given number of projects.
        repo = self.create_repo()
        for i in range(count):
            project = self.create_project(repository=repo)
            self.create_plan(project)
        return repo

    def assert_resp_has_multiple_items(self, resp, count):
        # Assert that the response is sane and contains count items.
        assert resp.status_code == 200, resp.data
        items = self.unserialize(resp)
        assert len(items) == count
        return items

    def assert_collection_id_across_builds(self, data):
        # Assert that all builds have the same collection id.
        assert len(data) > 0
        collection_id = data[0]['collection_id']
        assert collection_id
        print "collection_id", collection_id
        for build in data:
            assert build['collection_id'] == collection_id
