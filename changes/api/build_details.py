from sqlalchemy.orm import joinedload, subqueryload_all

from changes.api.base import APIView
from changes.models import Build, Test, Revision


class BuildDetailsAPIView(APIView):
    def get(self, build_id):
        build = Build.query.options(
            subqueryload_all(Build.phases),
            joinedload(Build.project),
            joinedload(Build.author),
            joinedload(Build.parent_revision),
            joinedload(Build.parent_revision, Revision.author),
        ).get(build_id)
        test_list = list(Test.query.filter_by(
            build_id=build.id).order_by('-result', '-duration'))

        context = {
            'build': build,
            'phases': build.phases,
            'tests': test_list,
        }

        return self.respond(context)
