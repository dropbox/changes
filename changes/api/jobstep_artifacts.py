from __future__ import absolute_import, division, unicode_literals

from flask_restful.reqparse import RequestParser
from sqlalchemy.exc import IntegrityError
from werkzeug.datastructures import FileStorage

from changes.api.base import APIView
from changes.config import db
from changes.constants import Result
from changes.models import Artifact, JobStep


class JobStepArtifactsAPIView(APIView):
    parser = RequestParser()
    parser.add_argument('name', type=unicode, required=True)
    parser.add_argument('file', type=FileStorage, dest='artifact_file',
                        location='files', required=True)

    def get(self, step_id):
        """
        Retrieve the artifacts for a JobStep.
        """
        if not JobStep.query.get(step_id):
            return self.respond({}, status_code=404)

        artifacts = Artifact.query.filter_by(step_id=step_id).all()
        return self.respond({'artifacts': artifacts})

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
            existing_msg = {"error": "An artifact with this name already exists"}
            return self.respond(existing_msg, status_code=204)

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

        return {'id': artifact.id.hex}, 201
