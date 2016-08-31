from collections import defaultdict

from changes.api.base import APIView
from changes.constants import Status
from changes.models.jobstep import JobStep
from changes.constants import DEFAULT_CPUS, DEFAULT_MEMORY_MB
from changes.models.jobplan import JobPlan
from flask_restful.reqparse import RequestParser
from flask_restful.types import boolean


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
    get_parser.add_argument('check_resources', type=boolean, location='args', default=False)

    def get(self):
        """GET method that returns aggregated data regarding jobsteps.
        Fetch pending, queued, allocated, and in-progress jobsteps from the database.
        Compute some aggregate metrics about them.
        Return the aggregated data in a JSON-friendly format.

        Args (in the form of a query string):
            status (Optional[str]): A specific status to look for.
                                    If not specified, will search all statuses.
            check_resources (Optional[bool]): If shown, adds cpu and memory data to output.

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
                'status value': {
                    'count': count of jobsteps in status,
                    'created': oldest jobstep create time,
                    'jobstep_id': jobstep_id of oldest,
                    'cpus': cpu sum of all jobsteps, only shown if check_resources is set
                    'mem': memory sum of all jobsteps, only shown if check_resources is set
                },
                ...
            }
        """
        args = self.get_parser.parse_args()

        buildstep_for_job_id = None
        default = {
            "count": 0,
            "created": None,
            "jobstep_id": None,
        }

        if args.check_resources:
            # cache of buildsteps, so we hit the db less
            buildstep_for_job_id = {}
            default.update({
                "cpus": 0,
                "mem": 0,
            })

        def process_row(agg, jobstep):
            status = jobstep.status.name
            current = agg.get(status) or default.copy()
            current['count'] += 1

            if args.check_resources:
                if jobstep.job_id not in buildstep_for_job_id:
                    buildstep_for_job_id[jobstep.job_id] = JobPlan.get_build_step_for_job(jobstep.job_id)[1]
                buildstep = buildstep_for_job_id[jobstep.job_id]
                limits = buildstep.get_resource_limits()
                req_cpus = limits.get('cpus', DEFAULT_CPUS)
                req_mem = limits.get('memory', DEFAULT_MEMORY_MB)

                current['cpus'] += req_cpus
                current['mem'] += req_mem

            # Track the oldest jobstep we've seen.
            if current['created'] is None or jobstep.date_created < current['created']:
                current['created'] = jobstep.date_created
                current['jobstep_id'] = jobstep.id
            agg[status] = current

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
