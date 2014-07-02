from changes.testutils import APITestCase
from changes.api.project_source_details import ProjectSourceDetailsAPIView


class ProjectSourceDetailsTest(APITestCase):
    def test_simple(self):
        project = self.create_project()
        source = self.create_source(project)

        path = '/api/0/projects/{0}/sources/{1}/'.format(
            project.id.hex, source.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == source.id.hex

    def test_filter_coverage_for_added_lines(self):
        view = ProjectSourceDetailsAPIView()
        diff = open('sample.diff').read()
        coverage = ['N'] * 150
        coverage[52] = 'C'
        coverage[53] = 'C'
        coverage[54] = 'C'
        coverage_dict = {'ci/run_with_retries.py': coverage}
        result = view._filter_coverage_for_added_lines(diff, coverage_dict)
        assert len(result) == 23  # 23 additions
        assert result == ['N', 'N', 'C', 'C', 'C', 'N', 'N', 'N', 'N', 'N', 'N', 'N', 'N', 'N', 'N', 'N', 'N', 'N', 'N', 'N', 'N', 'N', 'N']
