from buildbox.models import Build, Project, Author

from buildbox.web.base_handler import BaseRequestHandler


class BuildListHandler(BaseRequestHandler):
    def get(self):
        with self.db.get_session() as session:
            build_list = session.query(Build).join(Project).outerjoin(Author)

        context = {
            'build_list': build_list,
        }

        return self.render("build_list.html", **context)
