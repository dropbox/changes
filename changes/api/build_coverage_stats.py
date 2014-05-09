from flask.ext.restful import reqparse

from changes.api.base import APIView
from changes.lib.coverage import get_coverage_by_build_id
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
            parsed_diff = diff_parser.parse()

            files_in_diff = set(
                d['new_filename'][2:] for d in parsed_diff
                if d['new_filename']
            )

            results = [r for r in results if r.filename in files_in_diff]

        coverage = {
            c.filename: {
                'linesCovered': c.lines_covered,
                'linesUncovered': c.lines_uncovered,
                'diffLinesCovered': c.diff_lines_covered,
                'diffLinesUncovered': c.diff_lines_uncovered,
            }
            for c in results
        }

        return self.respond(coverage)
