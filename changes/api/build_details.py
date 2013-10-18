from flask import Response
from sqlalchemy.orm import joinedload, subqueryload_all

from changes.api.base import APIView
from changes.models import Build, Test


class BuildDetailsAPIView(APIView):
    def get(self, build_id):
        build = Build.query.options(
            subqueryload_all(Build.phases),
            joinedload(Build.project),
            joinedload(Build.author),
        ).get(build_id)
        if build is None:
            return Response(status=404)

        test_list = list(Test.query.filter_by(
            build_id=build.id).order_by(
                Test.result.desc(), Test.duration.desc()))

        context = {
            'build': build,
            'phases': build.phases,
            'tests': test_list,
        }

        return self.respond(context)

    def get_stream_channels(self, build_id):
        return [
            'builds:*:{0}'.format(build_id),
            'tests:*:{0}:*'.format(build_id),
        ]
