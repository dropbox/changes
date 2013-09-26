from sqlalchemy.orm import joinedload

from buildbox.models import Build, Revision
from buildbox.api.base import APIView


class BuildListAPIView(APIView):
    def get(self):
        build_list = list(
            Build.query.options(
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
