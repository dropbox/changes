from __future__ import absolute_import

from changes.constants import Status, Result
from changes.config import db
from changes.models import Project
from changes.jobs.update_project_stats import (
    update_project_stats, update_project_plan_stats
)
from changes.testutils import TestCase


class UpdateProjectStatsTest(TestCase):
    def test_simple(self):
        project = self.create_project()
        self.create_build(
            project=project,
            status=Status.finished,
            result=Result.passed,
            duration=5050,
        )

        update_project_stats(project_id=project.id.hex)

        db.session.expire(project)

        project = Project.query.get(project.id)

        assert project.avg_build_time == 5050


class UpdateProjectPlanStatsTest(TestCase):
    def test_simple(self):
        project = self.create_project()
        build = self.create_build(
            project=project,
            status=Status.finished,
            result=Result.passed,
            duration=5050,
        )
        job = self.create_job(build)
        plan = self.create_plan(project)
        self.create_job_plan(job, plan)

        update_project_plan_stats(
            project_id=project.id.hex,
            plan_id=plan.id.hex,
        )

        db.session.expire(plan)

        assert plan.avg_build_time == 5050
