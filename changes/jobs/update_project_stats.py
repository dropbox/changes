from changes.config import db
from changes.constants import Result, Status
from changes.models import Project, Job, JobPlan
from changes.utils.locking import lock


@lock
def update_project_stats(project_id):
    last_5_builds = Job.query.filter_by(
        result=Result.passed,
        status=Status.finished,
        project_id=project_id,
    ).order_by(Job.date_finished.desc())[:5]
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
        JobPlan, JobPlan.id == job_plan.id
    ).order_by(Job.date_finished.desc())[:5]
    if last_5_builds:
        avg_build_time = sum(
            b.duration for b in last_5_builds
            if b.duration
        ) / len(last_5_builds)
    else:
        avg_build_time = None

    db.session.query(JobPlan).filter(
        JobPlan.id == job_plan.id
    ).update({
        JobPlan.avg_build_time: avg_build_time,
    }, synchronize_session=False)
