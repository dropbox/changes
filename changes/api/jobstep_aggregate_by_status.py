from collections import defaultdict

from changes.api.base import APIView
from changes.constants import Status
from changes.models.jobstep import JobStep


class JobStepAggregateByStatusAPIView(APIView):
    def get(self):
        """GET method that returns aggregated data regarding jobsteps.
        Fetch pending, queued, and in-progress jobsteps from the database.
        Compute some aggregate metrics about them.
        Return the aggregated data in a JSON-friendly format.

        Returns:
            {
                'jobsteps': {
                    'by_cluster': {
                        '[some cluster id]': [status data],
                        ...
                    },
                    'by_project': {
                        '[some project slug]': [status data],
                    },
                    'global': [status_data],
                },
            }

            where [status_data] is:
            {
                'status value': [ count of jobsteps in status,
                                  oldest jobstep create time,
                                  jobstep_id of oldest ],
                ...
            }
        """
        def process_row(agg, jobstep):
            status = jobstep.status.name
            count, date_created, jobstep_id = agg.get(status, (0, None, None))
            count += 1

            # Track the oldest jobstep we've seen.
            if date_created is None or jobstep.date_created < date_created:
                date_created = jobstep.date_created
                jobstep_id = jobstep.id
            agg[status] = (count, date_created, jobstep_id)

        jobsteps = JobStep.query.filter(
            JobStep.status.in_(
                [Status.pending_allocation, Status.queued, Status.in_progress]),
        )

        by_cluster, by_project = defaultdict(dict), defaultdict(dict)
        by_global = {}
        for jobstep in jobsteps:
            process_row(by_cluster[jobstep.cluster], jobstep)
            process_row(by_project[jobstep.project.slug], jobstep)
            process_row(by_global, jobstep)

        output = {
            'jobsteps': {
                'by_cluster': by_cluster,
                'by_project': by_project,
                'global': by_global,
            },
        }
        return self.respond(output)
