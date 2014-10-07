from __future__ import absolute_import, division, unicode_literals

from datetime import datetime, timedelta
from sqlalchemy.sql import func

from changes.api.base import APIView
from changes.config import db
from changes.constants import Result, Status
from changes.models import Build, Job, JobStep


class SystemStatsAPIView(APIView):
    def _get_status_counts(self, cutoff):
        excluded = [Status.finished, Status.collecting_results, Status.unknown]

        build_stats = dict(db.session.query(
            Build.status,
            func.count(),
        ).filter(
            Build.date_created >= cutoff,
            ~Build.status.in_(excluded),
        ).group_by(
            Build.status,
        ))

        job_stats = dict(db.session.query(
            Job.status,
            func.count(),
        ).filter(
            Job.date_created >= cutoff,
            ~Job.status.in_(excluded),
        ).group_by(
            Job.status,
        ))

        jobstep_stats = dict(db.session.query(
            JobStep.status,
            func.count(),
        ).filter(
            JobStep.date_created >= cutoff,
            ~JobStep.status.in_(excluded),
        ).group_by(
            JobStep.status,
        ))

        context = []
        for status in Status.__members__.values():
            if status in excluded:
                continue

            if status == Status.pending_allocation:
                name = 'Pending Allocation'
            else:
                name = unicode(status)

            context.append({
                'name': name,
                'numBuilds': build_stats.get(status, 0),
                'numJobs': job_stats.get(status, 0),
                'numJobSteps': jobstep_stats.get(status, 0),
            })

        return context

    def _get_result_counts(self, cutoff):
        build_stats = dict(db.session.query(
            Build.result,
            func.count(),
        ).filter(
            Build.date_created >= cutoff,
            Build.status == Status.finished,
            Build.result != Result.unknown,
        ).group_by(
            Build.result,
        ))

        job_stats = dict(db.session.query(
            Job.result,
            func.count(),
        ).filter(
            Job.date_created >= cutoff,
            Job.status == Status.finished,
            Job.result != Result.unknown,
        ).group_by(
            Job.result,
        ))

        jobstep_stats = dict(db.session.query(
            JobStep.result,
            func.count(),
        ).filter(
            JobStep.date_created >= cutoff,
            JobStep.status == Status.finished,
            JobStep.result != Result.unknown,
        ).group_by(
            JobStep.result,
        ))

        context = []
        for result in Result.__members__.values():
            if result in (Result.unknown, Result.skipped):
                continue

            context.append({
                'name': unicode(result),
                'numBuilds': build_stats.get(result, 0),
                'numJobs': job_stats.get(result, 0),
                'numJobSteps': jobstep_stats.get(result, 0),
            })

        return context

    def get(self):
        cutoff = datetime.utcnow() - timedelta(hours=24)

        context = {
            'statusCounts': self._get_status_counts(cutoff),
            'resultCounts': self._get_result_counts(cutoff),
        }

        return self.respond(context, serialize=False)
