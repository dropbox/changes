from flask import Response
from sqlalchemy.orm import joinedload, subqueryload_all

from changes.api.base import APIView
from changes.models import Build, Test


class BuildDetailsAPIView(APIView):
    def get(self, change_id, build_id):
        try:
            build = Build.query.options(
                subqueryload_all(Build.phases),
                joinedload(Build.project),
                joinedload(Build.author),
            ).filter_by(change_id=change_id, id=build_id)[0]
        except IndexError:
            return Response(status=404)

        test_list = list(Test.query.filter_by(
            build_id=build.id).order_by('-result', '-duration'))

        context = {
            'build': build,
            'phases': build.phases,
            'tests': test_list,
        }

        return self.respond(context)

    def get_stream_channels(self, change_id, build_id):
        return ['builds:{0}:{1}'.format(change_id, build_id)]
