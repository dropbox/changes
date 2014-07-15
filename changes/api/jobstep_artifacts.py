from __future__ import absolute_import, division, unicode_literals

from flask_restful.reqparse import RequestParser
from werkzeug.datastructures import FileStorage

from changes.api.base import APIView
from changes.config import db
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

        args = self.parser.parse_args()

        artifact = Artifact(
            name=args.name,
            step_id=step.id,
            job_id=step.job_id,
            project_id=step.project_id,
        )
        db.session.add(artifact)
        db.session.flush()

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
