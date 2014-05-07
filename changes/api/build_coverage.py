from changes.api.base import APIView

from changes.constants import Status
from changes.models import Build, FileCoverage, Job


class BuildTestCoverageAPIView(APIView):
    def get(self, build_id):
        build = Build.query.get(build_id)
        if build is None:
            return '', 404

        return self.respond(self._get_coverage_by_source_id(build.source_id))

    # TODO(bryan): Move this into a lib function
    def _get_coverage_by_source_id(self, source_id):
        """
        Takes a source_id returns a dictionary of coverage for the source_id.  The coverage is
        generated for the most recent finished job.

        The dictionary maps file names to a string of the form 'UNCCCNCU', where U means
        'uncovered', C means 'covered' and 'N' means 'no coverage info'.

        If we don't have coverage info for a listed file, we leave it out of the dict.
        """
        # Grab the newest, finished job_id from the source
        newest_completed_job = Job.query.filter(
            Job.source_id == source_id,
            Job.status == Status.finished,
        ).order_by(Job.date_created.desc()).first()

        if not newest_completed_job:
            return {}

        # grab the filecoverage for that job and filenames
        all_file_coverages = FileCoverage.query.filter(
            FileCoverage.job_id == newest_completed_job.id,
        ).all()

        return {coverage.filename: coverage.data for coverage in all_file_coverages}
