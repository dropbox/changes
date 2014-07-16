from __future__ import absolute_import

from changes.api.base import APIView
from changes.config import db
from changes.models import Project, Snapshot


class ProjectSnapshotIndexAPIView(APIView):

    def get(self, project_id):
        project = Project.get(project_id)
        if not project:
            return '', 404

        queryset = Snapshot.query.filter(
            Snapshot.project_id == project.id,
        )

        return self.paginate(queryset)

    def post(self, project_id):
        """Initiates a new snapshot for this project."""
        project = Project.get(project_id)
        if not project:
            return '', 404

        # TODO(adegtiar): initialize a snapshot build.
        snapshot = Snapshot(
            project_id = project.id,
        )

        db.session.add(snapshot)
        db.session.commit()

        # TODO(adegtiar): execute the build.

        return self.respond(snapshot)
