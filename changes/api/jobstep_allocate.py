from __future__ import absolute_import, division, unicode_literals

import json
import logging

from flask import request
from sqlalchemy.sql import func

from changes.api.base import APIView, error
from changes.constants import Status, Result
from changes.config import db, redis, statsreporter
from changes.ext.redis import UnableToGetLock
from changes.models import Build, Job, JobPlan, JobStep


class JobStepAllocateAPIView(APIView):
    def find_next_jobsteps(self, limit=10):
        # find projects with pending allocations
        project_list = [p for p, in db.session.query(
            JobStep.project_id,
        ).filter(
            JobStep.status == Status.pending_allocation,
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

        filters = [
            JobStep.status == Status.pending_allocation,
        ]
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
            JobStep.status == Status.pending_allocation,
        )
        if results:
            queryset = queryset.filter(~JobStep.id.in_(q.id for q in results))
        results.extend(queryset[:limit - len(results)])
        return results[:limit]

    def post(self):
        args = json.loads(request.data)

        try:
            resources = args['resources']
        except KeyError:
            return error('Missing resources attribute')

        # cpu and mem as 0 are treated by changes-client
        # as having no enforced limit
        total_cpus = int(resources.get('cpus', 0))
        total_mem = int(resources.get('mem', 0))  # MB

        with statsreporter.stats().timer('jobstep_allocate'):
            try:
                with redis.lock('jobstep:allocate', nowait=True):
                    available_allocations = self.find_next_jobsteps(limit=10)
                    to_allocate = []
                    for jobstep in available_allocations:
                        req_cpus = jobstep.data.get('cpus', 4)
                        req_mem = jobstep.data.get('mem', 8 * 1024)

                        if total_cpus >= req_cpus and total_mem >= req_mem:
                            total_cpus -= req_cpus
                            total_mem -= req_mem

                            jobstep.status = Status.allocated
                            db.session.add(jobstep)

                            to_allocate.append(jobstep)
                        else:
                            logging.info('Not allocating %s due to lack of offered resources', jobstep.id.hex)

                    if not to_allocate:
                        # Should 204, but flask/werkzeug throws StopIteration (bug!) for tests
                        return self.respond([])

                    db.session.flush()
            except UnableToGetLock:
                return error('Another allocation is in progress', http_code=503)

            context = []

            for jobstep, jobstep_data in zip(to_allocate, self.serialize(to_allocate)):
                try:
                    jobplan, buildstep = JobPlan.get_build_step_for_job(jobstep.job_id)

                    assert jobplan and buildstep

                    jobstep_data['project'] = self.serialize(jobstep.project)
                    jobstep_data['resources'] = {
                        'cpus': jobstep.data.get('cpus', 4),
                        'mem': jobstep.data.get('mem', 8 * 1024),
                    }
                    jobstep_data['cmd'] = buildstep.get_allocation_command(jobstep)
                except Exception:
                    jobstep.status = Status.finished
                    jobstep.result = Result.infra_failed
                    db.session.add(jobstep)
                    db.session.flush()

                    logging.exception(
                        'Exception occurred while allocating job step %s for project %s',
                        jobstep.id.hex, jobstep.project.slug)
                else:
                    context.append(jobstep_data)

            return self.respond(context)
