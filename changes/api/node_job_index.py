from __future__ import absolute_import

from sqlalchemy.orm import joinedload

from changes.api.base import APIView
from changes.api.serializer.models.job import JobWithBuildCrumbler
from changes.models import Job, JobStep, Node


class NodeJobIndexAPIView(APIView):
    def get(self, node_id):
        node = Node.query.get(node_id)
        if node is None:
            return '', 404

        jobs = Job.query.join(
            JobStep, JobStep.job_id == Job.id,
        ).options(
            joinedload(Job.build, innerjoin=True),
        ).filter(
            JobStep.node_id == node.id,
        ).order_by(Job.date_created.desc())

        return self.paginate(jobs, serializers={
            Job: JobWithBuildCrumbler(),
        })
