from sqlalchemy.orm import joinedload, subqueryload_all

from buildbox.models import Build, Test, Revision
from buildbox.web.base_handler import BaseAPIRequestHandler


class BuildDetailsApiHandler(BaseAPIRequestHandler):
    def get(self, build_id):
        with self.db.get_session() as session:
            build = session.query(Build).options(
                subqueryload_all(Build.phases),
                joinedload(Build.project),
                joinedload(Build.author),
                joinedload(Build.parent_revision),
                joinedload(Build.parent_revision, Revision.author),
            ).get(build_id)
            test_list = list(session.query(Test).filter_by(
                build_id=build.id).order_by('-result', '-duration'))

        context = {
            'build': build,
            'phases': build.phases,
            'tests': test_list,
        }

        return self.respond(context)
