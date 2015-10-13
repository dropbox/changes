from flask.ext.restful import reqparse

from changes.api.base import APIView
from changes.lib.coverage import get_coverage_by_build_id, merged_coverage_data, get_coverage_stats
from changes.models import Build
from changes.utils.diff_parser import DiffParser


class BuildTestCoverageStatsAPIView(APIView):
    parser = reqparse.RequestParser()
    parser.add_argument('diff', action='store_true', default=False)

    def get(self, build_id):
        build = Build.query.get(build_id)
        if build is None:
            return '', 404

        args = self.parser.parse_args()

        results = get_coverage_by_build_id(build.id)

        if args.diff:
            diff = build.source.generate_diff()
            if not diff:
                return self.respond({})

            diff_parser = DiffParser(diff)
            lines_by_file = diff_parser.get_lines_by_file()

            results = [r for r in results if r.filename in lines_by_file]

            coverage_data = merged_coverage_data(results)

            coverage_stats = {}
            for filename in lines_by_file:
                if filename in coverage_data and filename in lines_by_file:
                    stats = get_coverage_stats(lines_by_file[filename], coverage_data[filename])
                    coverage_stats[filename] = {
                        'linesCovered': stats.lines_covered,
                        'linesUncovered': stats.lines_uncovered,
                        'diffLinesCovered': stats.diff_lines_covered,
                        'diffLinesUncovered': stats.diff_lines_uncovered,
                    }

        else:
            # NOTE: Without a diff, the stats may be off if there are
            # multiple job steps.  (Each job step can potentially
            # return a separate FileCoverage row for the same file.)
            # For each file, we return the best metrics using
            # min()/max(); if you want more correct metrics, pass
            # diff=1.
            coverage_stats = {}
            for r in results:
                if r.filename not in coverage_stats:
                    coverage_stats[r.filename] = {
                        'linesCovered': r.lines_covered,
                        'linesUncovered': r.lines_uncovered,
                        'diffLinesCovered': r.diff_lines_covered,
                        'diffLinesUncovered': r.diff_lines_uncovered,
                    }
                else:
                    # Combine metrics using max() for [diff] lines
                    # covered, min() for [diff] lines uncovered.
                    stats = coverage_stats[r.filename]
                    coverage_stats[r.filename] = {
                        'linesCovered': max(stats['linesCovered'], r.lines_covered),
                        'linesUncovered': min(stats['linesUncovered'], r.lines_uncovered),
                        'diffLinesCovered': max(stats['diffLinesCovered'], r.diff_lines_covered),
                        'diffLinesUncovered': min(stats['diffLinesUncovered'], r.diff_lines_uncovered),
                    }

        return self.respond(coverage_stats)
