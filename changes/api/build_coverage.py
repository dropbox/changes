from changes.api.base import APIView

from changes.lib.coverage import get_coverage_by_build_id

from changes.models import Build


class BuildTestCoverageAPIView(APIView):
    def get(self, build_id):
        build = Build.query.get(build_id)
        if build is None:
            return '', 404

        return self.respond(get_coverage_by_build_id(build.id))
