from __future__ import absolute_import

from flask.ext.restful.reqparse import RequestParser

from changes.config import db
from changes.db.utils import get_or_create
from changes.models import Project, Snapshot, Source
from changes.api.base import APIView
from changes.api.build_index import identify_revision, MissingRevision


class ProjectSnapshotIndexAPIView(APIView):
    post_parser = RequestParser()
    post_parser.add_argument('sha', type=str, required=True)

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

        args = self.post_parser.parse_args()

        repository = project.repository

        try:
            revision = identify_revision(repository, args.sha)
        except MissingRevision:
            # if the default fails, we absolutely can't continue and the
            # client should send a valid revision
            return '{"error": "Unable to find a matching revision."}', 400

        if revision:
            sha = revision.sha
        else:
            sha = args.sha

        source, _ = get_or_create(Source, where={
            'repository': repository,
            'revision_sha': sha,
        })

        # TODO(adegtiar): initialize a snapshot build.
        snapshot = Snapshot(
            project_id=project.id,
            source_id=source.id,
        )

        db.session.add(snapshot)
        db.session.commit()

        # TODO(adegtiar): execute the build.

        return self.respond(snapshot)
