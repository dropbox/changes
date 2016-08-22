from collections import defaultdict

from changes.api.base import APIView
from changes.constants import Status
from changes.models.jobstep import JobStep
from flask_restful.reqparse import RequestParser


def status_name(value, name):
    # type: (str, str) -> List[Status]
    try:
        return [Status[value]]
    except KeyError:
        raise ValueError("The status '{}' is not a known status name.".format(value))


class JobStepAggregateByStatusAPIView(APIView):
    get_parser = RequestParser()
    default_statuses = (Status.pending_allocation, Status.queued, Status.in_progress, Status.allocated)
    get_parser.add_argument('status', type=status_name, location='args', default=default_statuses)

    def get(self):
        """GET method that returns aggregated data regarding jobsteps.
        Fetch pending, queued, allocated, and in-progress jobsteps from the database.
        Compute some aggregate metrics about them.
        Return the aggregated data in a JSON-friendly format.

        Args (in the form of a query string):
            status (Optional[str]): A specific status to look for.
                                    If not specified, will search all statuses.

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

        args = self.get_parser.parse_args()
        jobsteps = JobStep.query.filter(
            JobStep.status.in_(args.status),
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
