from buildbox.models import Build

from buildbox.web.base_handler import BaseRequestHandler


class BuildListHandler(BaseRequestHandler):
    def get(self):
        with self.db.get_session() as session:
            build_list = session.query(Build).all()

        context = {
            'build_list': build_list,
        }

        return self.render("build_list.html", **context)
