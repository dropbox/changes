import uuid
import os.path

from cStringIO import StringIO
from mock import patch

from changes.artifacts.coverage import CoverageHandler
from changes.models import Job, JobStep, Source
from changes.models.filecoverage import FileCoverage
from changes.testutils import TestCase
from changes.testutils.fixtures import SAMPLE_COVERAGE, SAMPLE_DIFF


class CoverageHandlerTest(TestCase):
    def test_cobertura_result_generation(self):
        jobstep = JobStep(
            id=uuid.uuid4(),
            job=Job(id=uuid.uuid4(), project_id=uuid.uuid4())
        )

        fp = StringIO(SAMPLE_COVERAGE)

        handler = CoverageHandler(jobstep)
        results = handler.get_coverage(fp)

        assert len(results) == 2

        r1 = results[0]
        assert type(r1) == FileCoverage
        assert r1.job_id == jobstep.job.id
        assert r1.project_id == jobstep.job.project_id
        assert r1.filename == 'setup.py'
        assert r1.data == 'NUNNNNNNNNNUCCNU'
        r2 = results[1]
        assert type(r2) == FileCoverage
        assert r2.job_id == jobstep.job.id
        assert r2.project_id == jobstep.job.project_id
        assert r2.data == 'CUCNNNU'  # partial branch coverage is considered uncovered

    def test_empty_cobertura_file(self):
        jobstep = JobStep(
            id=uuid.uuid4(),
            job=Job(id=uuid.uuid4(), project_id=uuid.uuid4())
        )

        fp = StringIO('')

        handler = CoverageHandler(jobstep)
        results = handler.get_coverage(fp)

        # most importantly, it shouldn't crash
        assert len(results) == 0

    def test_jacoco_result_generation(self):
        jobstep = JobStep(
            id=uuid.uuid4(),
            job=Job(id=uuid.uuid4(), project_id=uuid.uuid4())
        )

        handler = CoverageHandler(jobstep)
        with open(os.path.join(os.path.dirname(__file__), 'fixtures', 'jacoco-coverage.xml')) as fp:
            results = handler.get_coverage(fp)

        assert len(results) == 1

        r1 = results[0]
        assert type(r1) == FileCoverage
        assert r1.job_id == jobstep.job.id
        assert r1.project_id == jobstep.job.project_id
        assert r1.filename == 'src/main/java/com/dropbox/apx/onyx/api/resource/stats/StatsResource.java'
        assert r1.data == 'NNNNCCCCNNCCUU'

    @patch.object(Source, 'generate_diff')
    def test_process_diff(self, generate_diff):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase)

        generate_diff.return_value = SAMPLE_DIFF

        handler = CoverageHandler(jobstep)

        lines_by_file = handler.get_processed_diff()
        # Just check the keys and one detail (there are other unittests that validate this already)
        assert set(lines_by_file) == {'ci/server-collect', 'ci/run_with_retries.py', 'ci/not-real'}
        assert lines_by_file['ci/not-real'] == {1}

        # This should be repeatable
        assert handler.get_processed_diff() == lines_by_file

    @patch.object(CoverageHandler, 'get_coverage')
    @patch.object(CoverageHandler, 'process_diff')
    def test_process(self, process_diff, get_coverage):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase)

        handler = CoverageHandler(jobstep)

        process_diff.return_value = {
            'setup.py': set([1, 2, 3, 4, 5]),
            'config.py': set([1, 3]),
        }

        # now try with some duplicate coverage
        get_coverage.return_value = [FileCoverage(
            job_id=job.id,
            step_id=jobstep.id,
            project_id=project.id,
            filename='setup.py',
            data='CUNNNNCCNNNUNNNUUUUUU'
        ), FileCoverage(
            job_id=job.id,
            step_id=jobstep.id,
            project_id=project.id,
            filename='config.py',
            data=''
        )]

        fp = StringIO()
        handler.process(fp)
        get_coverage.assert_called_once_with(fp)

        get_coverage.reset_mock()

        get_coverage.return_value = [FileCoverage(
            job_id=job.id,
            step_id=jobstep.id,
            project_id=project.id,
            filename='setup.py',
            data='NUUNNNNNNNNUCCNU'
        ), FileCoverage(
            job_id=job.id,
            step_id=jobstep.id,
            project_id=project.id,
            filename='config.py',
            data='U'
        )]

        fp = StringIO()
        handler.process(fp)
        get_coverage.assert_called_once_with(fp)

        get_coverage.reset_mock()

        get_coverage.return_value = [FileCoverage(
            job_id=job.id,
            step_id=jobstep.id,
            project_id=project.id,
            filename='setup.py',
            data='NUUNNNNNNNNUCCNU'
        ), FileCoverage(
            job_id=job.id,
            step_id=jobstep.id,
            project_id=project.id,
            filename='config.py',
            data='NNC'
        )]

        fp = StringIO()
        handler.process(fp)
        get_coverage.assert_called_once_with(fp)

        file_cov = list(FileCoverage.query.filter(
            FileCoverage.job_id == job.id,
        ))
        assert len(file_cov) == 2
        file_cov.sort(key=lambda r: -len(r.data))
        assert file_cov[0].filename == 'setup.py'
        assert file_cov[0].data == 'CUUNNNCCNNNUCCNUUUUUU'
        assert file_cov[0].lines_covered == 5
        assert file_cov[0].lines_uncovered == 9
        assert file_cov[0].diff_lines_covered == 1
        assert file_cov[0].diff_lines_uncovered == 2
        assert file_cov[1].filename == 'config.py'
        assert file_cov[1].data == 'UNC'
        assert file_cov[1].lines_covered == 1
        assert file_cov[1].lines_uncovered == 1
        assert file_cov[1].diff_lines_covered == 1
        assert file_cov[1].diff_lines_uncovered == 1
