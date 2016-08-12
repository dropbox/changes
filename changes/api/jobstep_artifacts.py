from __future__ import absolute_import, division, unicode_literals

from flask_restful.reqparse import RequestParser
from werkzeug.datastructures import FileStorage

from changes.api.base import APIView
from changes.models.artifact import Artifact
from changes.models.jobstep import JobStep


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
