from __future__ import absolute_import

from sqlalchemy.orm import joinedload

from changes.api.base import APIView
from changes.api.serializer.models.job import JobWithBuildCrumbler
from changes.models import Job, JobPlan, Snapshot


class SnapshotJobIndexAPIView(APIView):
    """Defines the endpoint for fetching jobs that use a given snapshot."""

    def get(self, snapshot_id):
        snapshot = Snapshot.query.get(snapshot_id)
        if snapshot is None:
            return self.respond({}, status_code=404)

        snapshot_image_ids = [image.id for image in snapshot.images]

        jobs = Job.query.join(
            JobPlan, JobPlan.job_id == Job.id,
        ).options(
            joinedload(Job.build, innerjoin=True),
        ).filter(
            JobPlan.snapshot_image_id.in_(snapshot_image_ids),
        ).order_by(Job.date_created.desc())

        return self.paginate(jobs, serializers={
            Job: JobWithBuildCrumbler(),
        })
