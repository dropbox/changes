from __future__ import absolute_import

from changes.constants import Status, Result
from changes.config import db
from changes.models import Project, ProjectPlan
from changes.jobs.update_project_stats import (
    update_project_stats, update_project_plan_stats
)
from changes.testutils import TestCase


class UpdateProjectStatsTest(TestCase):
    def test_simple(self):
        self.create_build(
            project=self.project,
            status=Status.finished,
            result=Result.passed,
            duration=5050,
        )

        update_project_stats(project_id=self.project.id.hex)

        db.session.expire(self.project)

        project = Project.query.get(self.project.id)

        assert project.avg_build_time == 5050


class UpdateProjectPlanStatsTest(TestCase):
    def test_simple(self):
        build = self.create_build(
            project=self.project,
            status=Status.finished,
            result=Result.passed,
            duration=5050,
        )
        job = self.create_job(build)
        plan = self.create_plan()
        plan.projects.append(self.project)
        self.create_job_plan(job, plan)

        update_project_plan_stats(
            project_id=self.project.id.hex,
            plan_id=plan.id.hex,
        )

        db.session.expire(plan)

        project_plan = ProjectPlan.query.filter(
            ProjectPlan.project_id == self.project.id,
            ProjectPlan.plan_id == plan.id,
        ).first()

        assert project_plan.avg_build_time == 5050
