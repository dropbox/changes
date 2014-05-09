import uuid

from cStringIO import StringIO
from mock import patch

from changes.models import Job, JobStep
from changes.models.filecoverage import FileCoverage
from changes.handlers.coverage import CoverageHandler
from changes.testutils import TestCase
from changes.testutils.fixtures import SAMPLE_COVERAGE


def test_result_generation():
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
    assert r2.data == 'CCCNNNU'


class CoverageHandlerTest(TestCase):
    @patch.object(CoverageHandler, 'get_coverage')
    def test_simple(self, get_coverage):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase)

        handler = CoverageHandler(jobstep)

        # now try with some duplicate coverage
        get_coverage.return_value = [FileCoverage(
            job_id=job.id,
            step_id=jobstep.id,
            project_id=project.id,
            filename='setup.py',
            data='CUNNNNCCNNNUNNNUUUUUU'
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
            data='NUNNNNNNNNNUCCNU'
        )]

        fp = StringIO()
        handler.process(fp)
        get_coverage.assert_called_once_with(fp)

        file_cov = list(FileCoverage.query.filter(
            FileCoverage.job_id == job.id,
        ))
        assert len(file_cov) == 1
        assert file_cov[0].filename == 'setup.py'
        assert file_cov[0].data == 'CUNNNNCCNNNUCCNUUUUUU'
