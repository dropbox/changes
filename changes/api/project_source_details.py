from __future__ import absolute_import, division, unicode_literals

from changes.api.base import APIView
from changes.constants import Status
from changes.models import FileCoverage, Job, Project, Source
import logging


class ProjectSourceDetailsAPIView(APIView):
    def get(self, project_id, source_id):
        project = Project.get(project_id)
        if not project:
            return '', 404

        repo = project.repository
        source = Source.query.filter(
            Source.id == source_id,
            Source.repository_id == repo.id,
        ).first()
        if source is None:
            return '', 404

        context = self.serialize(source)

        if source.patch:
            diff = source.patch.diff
        else:
            vcs = repo.get_vcs()
            if vcs:
                try:
                    diff = vcs.export(source.revision_sha)
                except Exception:
                    diff = None
            else:
                diff = None

        if diff:
            files = self._get_files_from_raw_diff(diff)
            coverage = self._get_coverage_by_source_id(source_id, files)
            coverage_for_added_lines = self._filter_coverage_for_added_lines(diff, coverage)
        else:
            coverage = None
            coverage_for_added_lines = None

        context['diff'] = diff
        context['coverage'] = coverage
        context['coverageForAddedLines'] = coverage_for_added_lines
        context['tails_data'] = dict(source.data)

        return self.respond(context)

    def _filter_coverage_for_added_lines(self, diff, coverage):
        """
        This function takes a diff (text based) and a map of file names to the coverage for those files and
        returns an ordered list of the coverage for each "addition" line in the diff.

        If we don't have coverage for a specific file, we just mark the lines in those files as unknown or 'N'.
        """
        if not diff:
            return None

        # Let's just encode it as utf-8 just in case
        diff_lines = diff.encode('utf-8').splitlines()

        current_file = None
        line_number = None
        coverage_by_added_line = []

        for line in diff_lines:
            if line.startswith('diff'):
                # We're about to start a new file.
                current_file = None
                line_number = None
            elif current_file is None and line_number is None and (line.startswith('+++') or line.startswith('---')):
                # We're starting a new file
                if line.startswith('+++ b/'):
                    line = line.split('\t')[0]
                    current_file = unicode(line[6:])
            elif line.startswith('@@'):
                # Jump to new lines within the file
                line_num_info = line.split('+')[1]
                line_number = int(line_num_info.split(',')[0]) - 1
            elif current_file is not None and line_number is not None:
                # Iterate through the file.
                if line.startswith('+'):
                    # Make sure we have coverage for this line.  Else just tag it as unknown.
                    cov = 'N'
                    if current_file in coverage:
                        try:
                            cov = coverage[current_file][line_number]
                        except IndexError:
                            logger = logging.getLogger('coverage')
                            logger.info('Missing code coverage for line %d of file %s' % (line_number, current_file))

                    coverage_by_added_line.append(cov)

                if not line.startswith('-'):
                    # Up the line count (assuming we aren't at a remove line)
                    line_number += 1

        return coverage_by_added_line

    def _get_files_from_raw_diff(self, diff):
        """
        Returns a list of filenames from a diff.
        """
        files = []
        diff_lines = diff.encode('utf-8').split('\n')
        for line in diff_lines:
            if line.startswith('+++ b/'):
                line = line.split('\t')[0]
                files += [unicode(line[6:])]

        return files

    def _get_coverage_by_source_id(self, source_id, files):
        """
        Takes a source_id and a list of file names and returns a dictionary of coverage for those
        files and source_id.  The coverage is generated for the most recent finished job.

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
            FileCoverage.filename.in_(files),
        ).all()

        return {coverage.filename: coverage.data for coverage in all_file_coverages}
