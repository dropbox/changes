from __future__ import absolute_import

from sqlalchemy.orm import joinedload

from changes.api.base import APIView
from changes.models import Artifact, Job


class JobArtifactIndexAPIView(APIView):
    def get(self, job_id):
        job = Job.query.get(job_id)
        if job is None:
            return '', 404

        queryset = Artifact.query.options(
            joinedload('step')
        ).filter(
            Artifact.job_id == job.id,
        ).order_by(
            Artifact.name.asc(),
        )

        return self.paginate(queryset)
