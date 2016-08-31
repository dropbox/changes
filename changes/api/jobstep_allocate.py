from __future__ import absolute_import, division, unicode_literals
import json
import logging
from collections import namedtuple
from datetime import datetime
from uuid import UUID
from flask import request
from flask_restful.reqparse import RequestParser
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import func
from changes.api.base import APIView, error
from changes.constants import Status
from changes.config import db, redis, statsreporter
from changes.ext.redis import UnableToGetLock
from changes.models.build import Build
from changes.models.job import Job
from changes.models.jobplan import JobPlan
from changes.models.jobstep import JobStep
from changes.constants import DEFAULT_CPUS, DEFAULT_MEMORY_MB

# Named tuple for data from the BuildStep used to pick JobSteps to allocate,
# to make sure we don't need to refetch (and risk inconsistency).
_AllocData = namedtuple('_AllocData', ['cpus', 'memory', 'command'])


class JobStepAllocateAPIView(APIView):
    def find_next_jobsteps(self, limit=10, cluster=None):
        cluster_filter = JobStep.cluster == cluster if cluster else JobStep.cluster.is_(None)

        # find projects with pending allocations
        project_list = [p for p, in db.session.query(
            JobStep.project_id,
        ).filter(
            JobStep.status == Status.pending_allocation,
            cluster_filter,
        ).group_by(
            JobStep.project_id
        )]
        if not project_list:
            return []

        # TODO(dcramer): this should be configurably and handle more cases
        # than just 'active job' as that can be 1 step or 100 steps
        # find the total number of job steps in progress per project
        # hard limit of 10 active jobs per project
        unavail_projects = [
            p for p, c in
            db.session.query(
                Job.project_id, func.count(Job.project_id),
            ).filter(
                Job.status.in_([Status.allocated, Status.in_progress]),
                Job.project_id.in_(project_list),
            ).group_by(
                Job.project_id,
            )
            if c >= 10
            ]

        base_filters = [
            JobStep.status == Status.pending_allocation,
            cluster_filter,
        ]
        filters = list(base_filters)
        if unavail_projects:
            filters.append(~JobStep.project_id.in_(unavail_projects))

        base_queryset = JobStep.query.join(
            Job, JobStep.job_id == Job.id,
        ).join(
            Build, Job.build_id == Build.id,
        ).order_by(Build.priority.desc(), JobStep.date_created.asc())

        # prioritize a job that's has already started
        queryset = list(base_queryset.filter(
            Job.status.in_([Status.allocated, Status.in_progress]),
            *filters
        )[:limit])
        if len(queryset) == limit:
            return queryset

        results = queryset

        # now allow any prioritized project, based on order
        queryset = base_queryset.filter(
            *filters
        )
        if results:
            queryset = queryset.filter(~JobStep.id.in_(q.id for q in results))
        results.extend(queryset[:limit - len(results)])
        if len(results) >= limit:
            return results[:limit]

        # TODO(dcramer): we want to burst but not go too far. For now just
        # let burst
        queryset = base_queryset.filter(
            *base_filters
        )
        if results:
            queryset = queryset.filter(~JobStep.id.in_(q.id for q in results))
        results.extend(queryset[:limit - len(results)])
        return results[:limit]

    get_parser = RequestParser()
    get_parser.add_argument('cluster', type=unicode, location='args', default=None)
    get_parser.add_argument('limit', type=int, location='args', default=200)

    def get(self):
        """
        GET method that returns a priority sorted list of possible jobsteps
        to allocate. The scheduler can then decide which ones it can actually
        allocate and makes a POST request to mark these as such with Changes.

        Args (in the form of a query string):
            cluster (Optional[str]): The cluster to look for jobsteps in.
            limit (int (default 200)): Maximum number of jobsteps to return.
        """
        args = self.get_parser.parse_args()

        cluster = args.cluster
        limit = args.limit

        with statsreporter.stats().timer('jobstep_allocate_get'):
            available_allocations = self.find_next_jobsteps(limit, cluster)
            jobstep_results = self.serialize(available_allocations)

            buildstep_for_job_id = {}
            for jobstep, jobstep_data in zip(available_allocations, jobstep_results):
                if jobstep.job_id not in buildstep_for_job_id:
                    buildstep_for_job_id[jobstep.job_id] = JobPlan.get_build_step_for_job(jobstep.job_id)[1]
                buildstep = buildstep_for_job_id[jobstep.job_id]
                limits = buildstep.get_resource_limits()
                req_cpus = limits.get('cpus', DEFAULT_CPUS)
                req_mem = limits.get('memory', DEFAULT_MEMORY_MB)
                allocation_cmd = buildstep.get_allocation_command(jobstep)
                jobstep_data['project'] = jobstep.project
                jobstep_data['resources'] = {
                    'cpus': req_cpus,
                    'mem': req_mem,
                }
                jobstep_data['cmd'] = allocation_cmd

            return self.respond({'jobsteps': jobstep_results})

    def post(self):
        """
        Allocates a list of jobstep IDs.
        This method of allocation works by first sending a GET request
        to get a priority sorted list of possible jobsteps. The scheduler can
        then allocate these as it sees fit, and sends a POST request with
        the list of jobstep IDs it actually decided to allocate.
        """
        args = json.loads(request.data)

        try:
            jobstep_ids = args['jobstep_ids']
        except KeyError:
            return error('Missing jobstep_ids attribute')

        for id in jobstep_ids:
            try:
                UUID(id)
            except ValueError:
                err = "Invalid jobstep id sent to jobstep_allocate: %s"
                logging.warning(err, id, exc_info=True)
                return error(err % id)

        cluster = args.get('cluster')

        with statsreporter.stats().timer('jobstep_allocate_post'):
            try:
                lock_key = 'jobstep:allocate'
                if cluster:
                    lock_key = lock_key + ':' + cluster
                with redis.lock(lock_key, nowait=True):
                    jobsteps = JobStep.query.filter(JobStep.id.in_(jobstep_ids))

                    for jobstep in jobsteps:
                        if jobstep.cluster != cluster:
                            db.session.rollback()
                            err = 'Jobstep is in cluster %s but tried to allocate in cluster %s (id=%s, project=%s)'
                            err_args = (jobstep.cluster, cluster, jobstep.id.hex, jobstep.project.slug)
                            logging.warning(err, *err_args)
                            return error(err % err_args)
                        if jobstep.status != Status.pending_allocation:
                            db.session.rollback()
                            err = 'Jobstep %s for project %s was already allocated'
                            err_args = (jobstep.id.hex, jobstep.project.slug)
                            logging.warning(err, *err_args)
                            return error(err % err_args, http_code=409)

                        jobstep.status = Status.allocated
                        db.session.add(jobstep)
                        # The JobSteps returned are pending_allocation, and the initial state for a Mesos JobStep is
                        # pending_allocation, so we can determine how long it was pending by how long ago it was
                        # created.
                        pending_seconds = (datetime.utcnow() - jobstep.date_created).total_seconds()
                        statsreporter.stats().log_timing('duration_pending_allocation', pending_seconds * 1000)

                    db.session.commit()

                    return self.respond({'allocated': jobstep_ids})
            except UnableToGetLock:
                return error('Another allocation is in progress', http_code=409)
            except IntegrityError:
                err = 'Could not commit allocation'
                logging.warning(err, exc_info=True)
                return error(err, http_code=409)
