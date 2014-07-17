from __future__ import absolute_import, division, unicode_literals

from flask_restful.reqparse import RequestParser
from sqlalchemy.exc import IntegrityError
from werkzeug.datastructures import FileStorage

from changes.api.base import APIView
from changes.config import db
from changes.constants import Result
from changes.jobs.sync_artifact import sync_artifact
from changes.models import Artifact, JobStep


class JobStepArtifactsAPIView(APIView):
    parser = RequestParser()
    parser.add_argument('name', type=unicode, required=True)
    parser.add_argument('file', type=FileStorage, dest='artifact_file',
                        location='files', required=True)

    def post(self, step_id):
        """
        Create a new artifact with the given name.
        """
        step = JobStep.query.get(step_id)
        if step is None:
            return '', 404

        if step.result == Result.aborted:
            return '', 410

        args = self.parser.parse_args()

        artifact = Artifact(
            name=args.name,
            step_id=step.id,
            job_id=step.job_id,
            project_id=step.project_id,
        )
        with db.session.begin_nested():
            try:
                db.session.add(artifact)
                db.session.flush()
            except IntegrityError:
                db.session.rollback()
                exists = True
            else:
                exists = False

        if exists:
            # XXX(dcramer); this is more of an error but we make an assumption
            # that this happens because it was already sent
            # TODO(dcramer): this should really return a different status code
            # but something in Flask/Flask-Restful is causing the test suite
            # to error if we return 204
            existing_msg = {"error": "An artifact with this name already exists"}
            return self.respond(existing_msg, status_code=200)

        step_id = artifact.step_id.hex
        artifact.file.save(
            args.artifact_file,
            '{0}/{1}/{2}_{3}'.format(
                step_id[:4], step_id[4:],
                artifact.id.hex, artifact.name
            ),
        )
        db.session.add(artifact)
        db.session.commit()

        sync_artifact.delay_if_needed(
            artifact_id=artifact.id.hex,
            task_id=artifact.id.hex,
            parent_task_id=step.id.hex,
        )

        return {'id': artifact.id.hex}, 201
