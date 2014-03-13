from __future__ import absolute_import

__all__ = ('Fixtures', 'SAMPLE_DIFF', 'SAMPLE_XUNIT')

from sqlalchemy.sql import func
from uuid import uuid4

from changes.config import db
from changes.db.funcs import coalesce
from changes.models import (
    Repository, Job, JobPlan, Project, Revision, Change, Author,
    TestGroup, Patch, Plan, Step, Build, Source, Node, JobPhase, JobStep, Task,
    Artifact, TestCase
)


SAMPLE_DIFF = """diff --git a/README.rst b/README.rst
index 2ef2938..ed80350 100644
--- a/README.rst
+++ b/README.rst
@@ -1,5 +1,5 @@
 Setup
------
+====="""

SAMPLE_XUNIT = """<?xml version="1.0" encoding="utf-8"?>
<testsuite errors="1" failures="0" name="" skips="0" tests="0" time="0.077">
    <testcase classname="" name="tests.test_report" time="0">
        <failure message="collection failure">tests/test_report.py:1: in &lt;module&gt;
&gt;   import mock
E   ImportError: No module named mock</failure>
    </testcase>
    <testcase classname="tests.test_report.ParseTestResultsTest" name="test_simple" time="0.00165796279907"/>
</testsuite>"""


class Fixtures(object):
    def create_repo(self, **kwargs):
        kwargs.setdefault('url', 'http://example.com/{0}'.format(uuid4().hex))

        repo = Repository(**kwargs)
        db.session.add(repo)

        return repo

    def create_node(self, **kwargs):
        kwargs.setdefault('label', uuid4().hex)

        node = Node(**kwargs)
        db.session.add(node)

        return node

    def create_project(self, **kwargs):
        if not kwargs.get('repository'):
            kwargs['repository'] = self.create_repo()
        kwargs['repository_id'] = kwargs['repository'].id
        kwargs.setdefault('name', uuid4().hex)
        kwargs.setdefault('slug', kwargs['name'])

        project = Project(**kwargs)
        db.session.add(project)

        return project

    def create_change(self, project, **kwargs):
        kwargs.setdefault('label', 'Sample')

        change = Change(
            hash=uuid4().hex,
            repository=project.repository,
            project=project,
            **kwargs
        )
        db.session.add(change)

        return change

    def create_test(self, job, **kwargs):
        kwargs.setdefault('name', uuid4().hex)

        case = TestCase(
            job=job,
            project=job.project,
            **kwargs
        )
        db.session.add(case)

        return case

    def create_testgroup(self, job, **kwargs):
        kwargs.setdefault('name', uuid4().hex)

        group = TestGroup(
            job=job,
            project=job.project,
            **kwargs
        )
        db.session.add(group)

        return group

    def create_job(self, build, **kwargs):
        project = build.project

        kwargs.setdefault('label', build.label)
        kwargs.setdefault('status', build.status)
        kwargs.setdefault('result', build.result)
        kwargs.setdefault('duration', build.duration)
        kwargs.setdefault('date_started', build.date_started)
        kwargs.setdefault('date_finished', build.date_finished)
        kwargs.setdefault('source', build.source)

        if kwargs.get('change', False) is False:
            kwargs['change'] = self.create_change(project)

        cur_no_query = db.session.query(
            coalesce(func.max(Job.number), 0)
        ).filter(
            Job.build_id == build.id,
        ).scalar()

        job = Job(
            build=build,
            build_id=build.id,
            number=cur_no_query + 1,
            project=project,
            project_id=project.id,
            **kwargs
        )
        db.session.add(job)

        return job

    def create_job_plan(self, job, plan):
        job_plan = JobPlan(
            project_id=job.project_id,
            build_id=job.build_id,
            plan_id=plan.id,
            job_id=job.id,
        )
        db.session.add(job_plan)

        return job_plan

    def create_source(self, project, **kwargs):
        kwargs.setdefault('revision_sha', uuid4().hex)

        source = Source(
            repository_id=project.repository_id,
            **kwargs
        )
        db.session.add(source)

        return source

    def create_build(self, project, **kwargs):
        if 'source' not in kwargs:
            kwargs['source'] = self.create_source(project)

        kwargs['source_id'] = kwargs['source'].id

        kwargs.setdefault('label', 'Sample')

        cur_no_query = db.session.query(
            coalesce(func.max(Build.number), 0)
        ).filter(
            Build.project_id == project.id,
        ).scalar()

        build = Build(
            number=cur_no_query + 1,
            repository_id=project.repository_id,
            repository=project.repository,
            project_id=project.id,
            project=project,
            **kwargs
        )
        db.session.add(build)

        return build

    def create_patch(self, project, **kwargs):
        kwargs.setdefault('label', 'Test Patch')
        kwargs.setdefault('message', 'Hello world!')
        kwargs.setdefault('diff', SAMPLE_DIFF)
        kwargs.setdefault('parent_revision_sha', uuid4().hex)
        if not kwargs.get('repository'):
            kwargs['repository'] = self.create_repo()
        kwargs['repository_id'] = kwargs['repository'].id

        patch = Patch(
            project=project,
            project_id=project.id,
            **kwargs
        )
        db.session.add(patch)

        return patch

    def create_revision(self, **kwargs):
        kwargs.setdefault('sha', uuid4().hex)
        if not kwargs.get('repository'):
            kwargs['repository'] = self.create_repo()

        if not kwargs.get('author'):
            kwargs['author'] = self.create_author()

        kwargs.setdefault('message', 'Test message')

        revision = Revision(**kwargs)
        db.session.add(revision)

        return revision

    def create_author(self, email=None, **kwargs):
        if not email:
            email = uuid4().hex + '@example.com'
        kwargs.setdefault('name', 'Test Case')

        author = Author(email=email, **kwargs)
        db.session.add(author)

        return author

    def create_plan(self, **kwargs):
        kwargs.setdefault('label', 'test')

        plan = Plan(**kwargs)
        db.session.add(plan)

        return plan

    def create_step(self, plan, **kwargs):
        kwargs.setdefault('implementation', 'test')
        kwargs.setdefault('order', 0)

        step = Step(plan=plan, **kwargs)
        db.session.add(step)

        return step

    def create_jobphase(self, job, **kwargs):
        kwargs.setdefault('label', 'test')

        phase = JobPhase(
            job=job,
            project=job.project,
            **kwargs
        )
        db.session.add(phase)

        return phase

    def create_jobstep(self, phase, **kwargs):
        kwargs.setdefault('label', 'test')

        step = JobStep(
            job=phase.job,
            project=phase.project,
            phase=phase,
            **kwargs
        )
        db.session.add(step)

        return step

    def create_task(self, **kwargs):
        task = Task(**kwargs)
        db.session.add(task)

        return task

    def create_artifact(self, step, **kwargs):
        artifact = Artifact(
            step=step,
            project=step.project,
            job=step.job,
            **kwargs
        )
        db.session.add(artifact)

        return artifact
