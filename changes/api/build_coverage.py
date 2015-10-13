from changes.api.base import APIView

from changes.lib.coverage import get_coverage_by_build_id, merged_coverage_data

from changes.models import Build


class BuildTestCoverageAPIView(APIView):
    def get(self, build_id):
        build = Build.query.get(build_id)
        if build is None:
            return '', 404

        coverage = merged_coverage_data(get_coverage_by_build_id(build.id))

        return self.respond(coverage)
