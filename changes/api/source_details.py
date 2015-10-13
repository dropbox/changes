from __future__ import absolute_import, division, unicode_literals

from changes.api.base import APIView
from changes.models import Source
from changes.lib.coverage import get_coverage_by_source_id, merged_coverage_data
import logging


class SourceDetailsAPIView(APIView):
    # this is mostly copy-pasted from ProjectSourceDetails :(

    def get(self, source_id):
        source = Source.query.filter(
            Source.id == source_id,
        ).first()
        if source is None:
            return '', 404

        context = self.serialize(source)

        diff = source.generate_diff()

        if diff:
            files = self._get_files_from_raw_diff(diff)

            coverage = merged_coverage_data(c for c in get_coverage_by_source_id(source_id)
                                            if c.filename in files)

            coverage_for_added_lines = self._filter_coverage_for_added_lines(diff, coverage)

            tails_info = dict(source.data)
        else:
            coverage = None
            coverage_for_added_lines = None
            tails_info = None

        context['diff'] = diff
        context['coverage'] = coverage
        context['coverageForAddedLines'] = coverage_for_added_lines
        context['tailsInfo'] = tails_info

        return self.respond(context)

    def _filter_coverage_for_added_lines(self, diff, coverage):
        """
        This function takes a diff (text based) and a map of file names to the coverage for those files and
        returns an ordered list of the coverage for each "addition" line in the diff.

        If we don't have coverage for a specific file, we just mark the lines in those files as unknown or 'N'.
        """
        if not diff:
            return None

        diff_lines = diff.splitlines()

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
                # Strip off the trailing ' @@' so that when only the line is specified
                # and there is no comma, we can just parse as a number.
                line_num_info = line_num_info.rstrip("@ ")
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
        files = set()
        diff_lines = diff.split('\n')
        for line in diff_lines:
            if line.startswith('+++ b/'):
                line = line.split('\t')[0]
                files.add(line[6:])

        return files
