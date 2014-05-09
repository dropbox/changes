from changes.config import db

from changes.constants import Status

from changes.models import Build, FileCoverage, Job, Project, Source


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
        newest_build_ids.add(db.session.query(Build.id).filter(
                Build.project_id == project.id,
                Build.source_id == source_id,
                Build.status == Status.finished
        ).order_by(Build.date_created.desc()).first()[0])

    return get_coverage_by_build_ids(newest_build_ids)


def get_coverage_by_build_id(build_id):
    return get_coverage_by_build_ids([build_id])


def get_coverage_by_build_ids(build_ids):
    """
    Returns the coverage associated with some builds.

    The dictionary maps file names to a string of the form 'UNCCCNCU', where U means
    'uncovered', C means 'covered' and 'N' means 'no coverage info'.
    """
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
    all_coverages = FileCoverage.query.filter(
        FileCoverage.job_id.in_(job_ids)
    )

    combined_file_coverage = dict()

    for coverage in all_coverages:
        combined_file_coverage[coverage.filename] = coverage.data

    return combined_file_coverage
