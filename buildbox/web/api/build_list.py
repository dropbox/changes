from sqlalchemy.orm import joinedload

from buildbox.models import Build, Revision
from buildbox.web.base_handler import BaseAPIRequestHandler


class BuildListApiHandler(BaseAPIRequestHandler):
    def get(self):
        with self.db.get_session() as session:
            build_list = list(
                session.query(Build).options(
                    joinedload(Build.project),
                    joinedload(Build.author),
                    joinedload(Build.parent_revision),
                    joinedload(Build.parent_revision, Revision.author),
                ).order_by(Build.date_created.desc())
            )[:100]

        context = {
            'builds': build_list,
        }

        return self.respond(context)
