from sqlalchemy import and_

from changes.config import db
from changes.constants import Result, Status
from changes.models.build import Build
from changes.models.job import Job
from changes.models.jobplan import JobPlan
from changes.models.plan import Plan
from changes.models.project import Project
from changes.utils.locking import lock


@lock
def update_project_stats(project_id):
    last_5_builds = Build.query.filter_by(
        result=Result.passed,
        status=Status.finished,
        project_id=project_id,
    ).order_by(Build.date_finished.desc())[:5]
    if last_5_builds:
        avg_build_time = sum(
            b.duration for b in last_5_builds
            if b.duration
        ) / len(last_5_builds)
    else:
        avg_build_time = None

    db.session.query(Project).filter(
        Project.id == project_id
    ).update({
        Project.avg_build_time: avg_build_time,
    }, synchronize_session=False)


@lock
def update_project_plan_stats(project_id, plan_id):
    job_plan = JobPlan.query.filter(
        JobPlan.project_id == project_id,
        JobPlan.plan_id == plan_id,
    ).first()
    if not job_plan:
        return

    last_5_builds = Job.query.filter(
        Job.result == Result.passed,
        Job.status == Status.finished,
        Job.project_id == project_id,
    ).join(
        JobPlan,
        and_(
            JobPlan.id == job_plan.id,
            JobPlan.job_id == Job.id,
        )
    ).order_by(Job.date_finished.desc())[:5]
    if last_5_builds:
        avg_build_time = sum(
            b.duration for b in last_5_builds
            if b.duration
        ) / len(last_5_builds)
    else:
        avg_build_time = None

    db.session.query(Plan).filter(
        Plan.id == job_plan.plan_id,
    ).update({
        Plan.avg_build_time: avg_build_time,
    }, synchronize_session=False)
