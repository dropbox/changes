from changes.api.base import APIView, error
from changes.models.build import Build
from changes.models.buildmessage import BuildMessage


class BuildMessageIndexAPIView(APIView):
    def get(self, build_id):
        build = Build.query.get(build_id)
        if not build:
            return error('build not found', http_code=404)
        queryset = BuildMessage.query.filter(
            BuildMessage.build_id == build.id,
        ).order_by(BuildMessage.date_created.asc())

        return self.paginate(queryset)
