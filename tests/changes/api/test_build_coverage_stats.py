from datetime import datetime
from mock import patch

from changes.config import db
from changes.constants import Status
from changes.models import FileCoverage
from changes.testutils import APITestCase
from changes.testutils.fixtures import SAMPLE_DIFF


class BuildCoverageStatsTest(APITestCase):
    @patch('changes.models.Source.generate_diff')
    def test_simple(self, generate_diff):
        project = self.create_project()
        build = self.create_build(
            project, date_created=datetime(2013, 9, 19, 22, 15, 24),
            status=Status.finished)
        job1 = self.create_job(build)
        job2 = self.create_job(build)

        db.session.add(FileCoverage(
            project_id=project.id,
            job_id=job1.id, filename='ci/run_with_retries.py',
            lines_covered=4, lines_uncovered=5, diff_lines_covered=2, diff_lines_uncovered=3,
            data='NNCCUU' + 'N' * 50 + 'CCUUU',  # Matches sample.diff
        ))
        db.session.add(FileCoverage(
            project_id=project.id,
            job_id=job2.id, filename='foobar.py',
            lines_covered=4, lines_uncovered=5, diff_lines_covered=2, diff_lines_uncovered=3,
            data='NNCCUU' + 'N' * 50 + 'CCUUU',  # Matches sample.diff
        ))
        # Two more not in sample.diff, same filename but different job ids
        db.session.add(FileCoverage(
            project_id=project.id,
            job_id=job1.id, filename='booh.py',
            lines_covered=4, lines_uncovered=5, diff_lines_covered=3, diff_lines_uncovered=2,
        ))
        db.session.add(FileCoverage(
            project_id=project.id,
            job_id=job2.id, filename='booh.py',
            lines_covered=5, lines_uncovered=4, diff_lines_covered=2, diff_lines_uncovered=3,
        ))
        db.session.commit()

        path = '/api/0/builds/{0}/stats/coverage/'.format(build.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 3
        assert data['ci/run_with_retries.py'] == {
            'linesCovered': 4,
            'linesUncovered': 5,
            'diffLinesCovered': 2,
            'diffLinesUncovered': 3,
        }
        assert data['foobar.py'] == {
            'linesCovered': 4,
            'linesUncovered': 5,
            'diffLinesCovered': 2,
            'diffLinesUncovered': 3,
        }
        assert data['booh.py'] == {
            'linesCovered': 5,
            'linesUncovered': 4,
            'diffLinesCovered': 3,
            'diffLinesUncovered': 2,
        }

        generate_diff.return_value = None

        resp = self.client.get(path + '?diff=1')
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 0

        generate_diff.return_value = SAMPLE_DIFF

        resp = self.client.get(path + '?diff=1')
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data['ci/run_with_retries.py'] == {
            'linesCovered': 4,
            'linesUncovered': 5,
            'diffLinesCovered': 2,
            'diffLinesUncovered': 3,
        }
