from collections import namedtuple

from changes.config import db
from changes.constants import Status
from changes.models.build import Build
from changes.models.filecoverage import FileCoverage
from changes.models.job import Job
from changes.models.project import Project
from changes.models.source import Source


def get_coverage_by_source_id(source_id):
    """
    Takes a source_id and returns a dictionary of coverage for that source_id.  The
    coverage is generated for the most recently finished builds for each project.

    The dictionary maps file names to a string of the form 'UNCCCNCU', where U means
    'uncovered', C means 'covered' and 'N' means 'no coverage info'.
    """
    source = Source.query.get(source_id)

    projects = Project.query.filter(
        Project.repository_id == source.repository_id
    )

    newest_build_ids = set()
    for project in projects:
        b_id = db.session.query(Build.id).filter(
            Build.project_id == project.id,
            Build.source_id == source_id,
            Build.status == Status.finished
        ).order_by(Build.date_created.desc()).first()
        if b_id:
            newest_build_ids.add(b_id[0])

    return get_coverage_by_build_ids(newest_build_ids)


def get_coverage_by_build_id(build_id):
    return get_coverage_by_build_ids([build_id])


def get_coverage_by_build_ids(build_ids):
    """
    Returns the coverage associated with some builds.

    The dictionary maps file names to a string of the form 'UNCCCNCU', where U means
    'uncovered', C means 'covered' and 'N' means 'no coverage info'.
    """
    if not build_ids:
        return {}

    all_job_ids = db.session.query(Job.id).filter(
        Job.build_id.in_(build_ids)
    )

    return get_coverage_by_job_ids(all_job_ids)


def get_coverage_by_job_ids(job_ids):
    """
    Returns the coverage associated with some jobs.

    The dictionary maps file names to a string of the form 'UNCCCNCU', where U means
    'uncovered', C means 'covered' and 'N' means 'no coverage info'.
    """
    if not job_ids:
        return {}

    return FileCoverage.query.filter(
        FileCoverage.job_id.in_(job_ids)
    )


def merge_coverage(old, new):
    """Merge two coverage strings.

    Each of the arguments is compact coverage data as described for
    get_coverage_by_job_ids(), and so is the return value.

    The merged string contains the 'stronger' or the two corresponding
    characters, where 'C' defeats 'U' and both defeat 'N'.
    """
    cov_data = []
    for lineno in range(max(len(old), len(new))):
        try:
            old_cov = old[lineno]
        except IndexError:
            old_cov = 'N'

        try:
            new_cov = new[lineno]
        except IndexError:
            new_cov = 'N'

        if old_cov == 'C' or new_cov == 'C':
            cov_data.append('C')
        elif old_cov == 'U' or new_cov == 'U':
            cov_data.append('U')
        else:
            cov_data.append('N')
    return ''.join(cov_data)


def merged_coverage_data(coverages):
    """Return a dict of merged coverage data by filename.

    The argument is an iterable of FileCoverage instances.  The return
    value is a dict mapping filenames to the merged coverage data in
    the form as described for get_coverage_by_job_ids().
    """
    coverage = {}
    for c in coverages:
        data = coverage.get(c.filename)
        if data:
            data = merge_coverage(data, c.data)
        else:
            data = c.data
        coverage[c.filename] = data
    return coverage


CoverageStats = namedtuple(
    'CoverageStats',
    ['lines_covered', 'lines_uncovered', 'diff_lines_covered', 'diff_lines_uncovered'])


def get_coverage_stats(diff_lines, data):
    """Return a tuple of coverage stats."""

    lines_covered = 0
    lines_uncovered = 0
    diff_lines_covered = 0
    diff_lines_uncovered = 0

    for lineno, code in enumerate(data):
        # lineno is 1-based in diff
        line_in_diff = bool((lineno + 1) in diff_lines)
        if code == 'C':
            lines_covered += 1
            if line_in_diff:
                diff_lines_covered += 1
        elif code == 'U':
            lines_uncovered += 1
            if line_in_diff:
                diff_lines_uncovered += 1

    return CoverageStats(lines_covered, lines_uncovered, diff_lines_covered, diff_lines_uncovered)
