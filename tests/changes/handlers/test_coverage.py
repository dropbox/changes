import uuid

from cStringIO import StringIO

from changes.models import Job, JobStep
from changes.models.filecoverage import FileCoverage
from changes.handlers.coverage import CoverageHandler
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
