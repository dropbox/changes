from sqlalchemy.orm import joinedload

from buildbox.models import Build
from buildbox.web.base_handler import BaseRequestHandler


class BuildListHandler(BaseRequestHandler):
    def get(self):
        with self.db.get_session() as session:
            build_list = list(
                session.query(Build).options(
                    joinedload(Build.project),
                    joinedload(Build.author),
                ).order_by(Build.date_created.desc())
            )[:100]

        context = {
            'build_list': build_list,
        }

        return self.render("build_list.html", **context)
