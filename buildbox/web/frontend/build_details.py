from sqlalchemy.orm import subqueryload_all, joinedload

from buildbox.models import (
    Project, Build, Phase, Step, Test, Revision, Author
)
from buildbox.web.base_handler import BaseRequestHandler


class BuildDetailsHandler(BaseRequestHandler):
    def get(self, project_slug, build_id):
        with self.db.get_session() as session:
            project = session.query(Project).filter_by(slug=project_slug)[0]
            build = session.query(Build).options(
                subqueryload_all(Build.phases, Phase.steps),
                joinedload(Build.author),
                joinedload(Build.parent_revision),
            ).get(build_id)
            assert build.project == project
            test_list = list(session.query(Test).filter_by(
                build_id=build.id).order_by('-result', '-duration'))

        context = {
            'project': project,
            'build': build,
            'test_list': test_list,
        }

        return self.render("build_details.html", **context)
