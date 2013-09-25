from sqlalchemy.orm import joinedload

from buildbox.models import Build
from buildbox.web.base_handler import APIRequestHandler


class BuildListApiHandler(APIRequestHandler):
    def get(self):
        with self.db.get_session() as session:
            build_list = list(
                session.query(Build).options(
                    joinedload(Build.project),
                    joinedload(Build.author),
                ).order_by(Build.date_created.desc())
            )[:100]

        context = {
            'builds': build_list,
        }

        return self.respond(context)
