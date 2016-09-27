import mock

from changes.constants import Result, ResultSource, Status
from changes.listeners.revision_result import create_or_update_revision_result, revision_result_build_finished_handler
from changes.models.revisionresult import RevisionResult
from changes.testutils.cases import TestCase


class TestRevisionResultBuildFinishedHandler(TestCase):
    def test_commit_build(self):
        build = self.create_build(self.create_project())
        with mock.patch('changes.listeners.revision_result.create_or_update_revision_result') as mocked:
            revision_result_build_finished_handler(build.id)
        mocked.assert_called_once_with(revision_sha=build.source.revision_sha, project_id=build.project_id, propagation_limit=1)

    def test_diff_build(self):
        project = self.create_project()
        source = self.create_source(project, patch=self.create_patch())
        build = self.create_build(project, source=source)
        with mock.patch('changes.listeners.revision_result.create_or_update_revision_result') as mocked:
            revision_result_build_finished_handler(build.id)
        assert mocked.call_count == 0


class TestCreateOrUpdateRevisionResultTestCase(TestCase):
    def test_no_unaffected_targets(self):
        build = self.create_build(self.create_project(), status=Status.finished, result=Result.passed)
        self.create_job(build, result=Result.passed)
        self.create_job(build, result=Result.passed)
        self.create_job(build, result=Result.passed)

        create_or_update_revision_result(build.source.revision_sha, build.project_id, propagation_limit=0)

        revision_result = RevisionResult.query.filter(
            RevisionResult.project_id == build.project_id,
            RevisionResult.revision_sha == build.source.revision_sha,
        ).first()

        assert revision_result is not None
        assert revision_result.build == build
        assert revision_result.result is Result.passed

    def test_no_unaffected_targets_with_existing_revision_result(self):
        build = self.create_build(self.create_project(), status=Status.finished, result=Result.passed)
        self.create_job(build, result=Result.passed)
        self.create_job(build, result=Result.passed)
        self.create_job(build, result=Result.passed)

        revision_result = self.create_revision_result(project=build.project, revision_sha=build.source.revision_sha)
        create_or_update_revision_result(build.source.revision_sha, build.project_id, propagation_limit=0)

        revision_result = RevisionResult.query.filter(
            RevisionResult.project_id == build.project_id,
            RevisionResult.revision_sha == build.source.revision_sha,
        ).first()

        assert revision_result is not None
        assert revision_result.build == build
        assert revision_result.result is Result.passed

    def test_with_unaffected_targets_no_parent_build(self):
        project = self.create_project()
        parent_revision = self.create_revision(repository=project.repository)

        revision = self.create_revision(parents=[parent_revision.sha], repository=project.repository)
        source = self.create_source(project, revision_sha=revision.sha)
        build = self.create_build(project, source=source, status=Status.finished, result=Result.passed)
        self.create_job(build, result=Result.passed)
        self.create_job(build, result=Result.passed)
        job = self.create_job(build, result=Result.passed)

        self.create_target(job, jobstep=None, result_source=ResultSource.from_parent, name='//target1:test')
        self.create_target(job, jobstep=None, result_source=ResultSource.from_parent, name='//target2:test')

        create_or_update_revision_result(build.source.revision_sha, build.project_id, propagation_limit=0)

        revision_result = RevisionResult.query.filter(
            RevisionResult.project_id == build.project_id,
            RevisionResult.revision_sha == build.source.revision_sha,
        ).first()

        assert revision_result is not None
        assert revision_result.build == build
        assert revision_result.result is Result.unknown

    def test_with_unaffected_targets_incomplete_targets(self):
        project = self.create_project()
        plan = self.create_plan(project)

        parent_revision = self.create_revision(repository=project.repository)
        parent_source = self.create_source(project, revision_sha=parent_revision.sha)
        parent_build = self.create_build(project, source=parent_source, status=Status.finished)
        parent_job = self.create_job(parent_build)
        self.create_job_plan(job=parent_job, plan=plan)
        self.create_target(parent_job, jobstep=None, name='//target1:test', result=Result.passed)
        self.create_target(parent_job, jobstep=None, name='//other:test', result=Result.passed)

        revision = self.create_revision(parents=[parent_revision.sha], repository=project.repository)
        source = self.create_source(project, revision_sha=revision.sha)
        build = self.create_build(project, source=source, status=Status.finished, result=Result.passed)
        self.create_job(build, result=Result.passed)
        self.create_job(build, result=Result.passed)
        job = self.create_job(build, result=Result.passed)
        self.create_job_plan(job=job, plan=plan)

        target1 = self.create_target(job, jobstep=None, result_source=ResultSource.from_parent, name='//target1:test')
        target2 = self.create_target(job, jobstep=None, result_source=ResultSource.from_parent, name='//target2:test')

        create_or_update_revision_result(build.source.revision_sha, build.project_id, propagation_limit=0)

        revision_result = RevisionResult.query.filter(
            RevisionResult.project_id == build.project_id,
            RevisionResult.revision_sha == build.source.revision_sha,
        ).first()

        assert revision_result is not None
        assert revision_result.build == build
        assert revision_result.result is Result.unknown
        assert target1.result is Result.passed
        assert target2.result is Result.unknown

    def test_with_unaffected_targets_incomplete_targets_failing(self):
        project = self.create_project()
        plan = self.create_plan(project)

        parent_revision = self.create_revision(repository=project.repository)
        parent_source = self.create_source(project, revision_sha=parent_revision.sha)
        parent_build = self.create_build(project, source=parent_source, status=Status.finished)
        parent_job = self.create_job(parent_build)
        self.create_job_plan(job=parent_job, plan=plan)
        self.create_target(parent_job, jobstep=None, name='//target1:test', result=Result.failed)
        self.create_target(parent_job, jobstep=None, name='//other:test', result=Result.passed)

        revision = self.create_revision(parents=[parent_revision.sha], repository=project.repository)
        source = self.create_source(project, revision_sha=revision.sha)
        build = self.create_build(project, source=source, status=Status.finished, result=Result.passed)
        self.create_job(build, result=Result.passed)
        self.create_job(build, result=Result.passed)
        job = self.create_job(build, result=Result.passed)
        self.create_job_plan(job=job, plan=plan)

        target1 = self.create_target(job, jobstep=None, result_source=ResultSource.from_parent, name='//target1:test')
        target2 = self.create_target(job, jobstep=None, result_source=ResultSource.from_parent, name='//target2:test')

        create_or_update_revision_result(build.source.revision_sha, build.project_id, propagation_limit=0)

        revision_result = RevisionResult.query.filter(
            RevisionResult.project_id == build.project_id,
            RevisionResult.revision_sha == build.source.revision_sha,
        ).first()

        assert revision_result is not None
        assert revision_result.build == build
        assert revision_result.result is Result.failed
        assert target1.result is Result.failed
        assert target2.result is Result.unknown

    def test_with_unaffected_targets_passed(self):
        project = self.create_project()
        plan = self.create_plan(project)

        parent_revision = self.create_revision(repository=project.repository)
        parent_source = self.create_source(project, revision_sha=parent_revision.sha)
        parent_build = self.create_build(project, source=parent_source, status=Status.finished)
        parent_job = self.create_job(parent_build)
        self.create_job_plan(job=parent_job, plan=plan)
        self.create_target(parent_job, jobstep=None, name='//target1:test', result=Result.passed)
        self.create_target(parent_job, jobstep=None, name='//target2:test', result=Result.passed)
        self.create_target(parent_job, jobstep=None, name='//other:test', result=Result.passed)

        revision = self.create_revision(parents=[parent_revision.sha], repository=project.repository)
        source = self.create_source(project, revision_sha=revision.sha)
        build = self.create_build(project, source=source, status=Status.finished, result=Result.passed)
        self.create_job(build, result=Result.passed)
        self.create_job(build, result=Result.passed)
        job = self.create_job(build, result=Result.passed)
        self.create_job_plan(job=job, plan=plan)

        target1 = self.create_target(job, jobstep=None, result_source=ResultSource.from_parent, name='//target1:test')
        target2 = self.create_target(job, jobstep=None, result_source=ResultSource.from_parent, name='//target2:test')

        create_or_update_revision_result(build.source.revision_sha, build.project_id, propagation_limit=0)

        revision_result = RevisionResult.query.filter(
            RevisionResult.project_id == build.project_id,
            RevisionResult.revision_sha == build.source.revision_sha,
        ).first()

        assert revision_result is not None
        assert revision_result.build == build
        assert revision_result.result is Result.passed
        assert target1.result is Result.passed
        assert target2.result is Result.passed

    def test_with_unaffected_targets_wrong_plan(self):
        project = self.create_project()
        plan = self.create_plan(project)

        parent_revision = self.create_revision(repository=project.repository)
        parent_source = self.create_source(project, revision_sha=parent_revision.sha)
        parent_build = self.create_build(project, source=parent_source, status=Status.finished)
        parent_job = self.create_job(parent_build)
        self.create_job_plan(job=parent_job, plan=plan)
        self.create_target(parent_job, jobstep=None, name='//target1:test', result=Result.passed)
        self.create_target(parent_job, jobstep=None, name='//target2:test', result=Result.passed)
        self.create_target(parent_job, jobstep=None, name='//other:test', result=Result.passed)

        revision = self.create_revision(parents=[parent_revision.sha], repository=project.repository)
        source = self.create_source(project, revision_sha=revision.sha)
        build = self.create_build(project, source=source, status=Status.finished, result=Result.passed)
        self.create_job(build, result=Result.passed)
        self.create_job(build, result=Result.passed)
        job = self.create_job(build, result=Result.passed)
        self.create_job_plan(job=job, plan=self.create_plan(project))

        target1 = self.create_target(job, jobstep=None, result_source=ResultSource.from_parent, name='//target1:test')
        target2 = self.create_target(job, jobstep=None, result_source=ResultSource.from_parent, name='//target2:test')

        create_or_update_revision_result(build.source.revision_sha, build.project_id, propagation_limit=0)

        revision_result = RevisionResult.query.filter(
            RevisionResult.project_id == build.project_id,
            RevisionResult.revision_sha == build.source.revision_sha,
        ).first()

        assert revision_result is not None
        assert revision_result.build == build
        assert revision_result.result is Result.unknown
        assert target1.result is Result.unknown
        assert target2.result is Result.unknown

    def test_with_propagation(self):
        project = self.create_project()

        revision = self.create_revision(repository=project.repository)
        source = self.create_source(project, revision_sha=revision.sha)
        build = self.create_build(project, source=source, status=Status.finished, result=Result.passed)

        child_revision = self.create_revision(repository=project.repository, parents=[revision.sha])

        with mock.patch('changes.listeners.revision_result.create_or_update_revision_result') as mocked:
            create_or_update_revision_result(build.source.revision_sha, build.project_id, propagation_limit=1)

        revision_result = RevisionResult.query.filter(
            RevisionResult.project_id == build.project_id,
            RevisionResult.revision_sha == build.source.revision_sha,
        ).first()

        assert revision_result is not None
        assert revision_result.build == build
        assert revision_result.result is Result.passed

        mocked.assert_called_once_with(child_revision.sha, project.id, propagation_limit=0)

    def test_with_propagation_no_count(self):
        project = self.create_project()

        revision = self.create_revision(repository=project.repository)
        source = self.create_source(project, revision_sha=revision.sha)
        build = self.create_build(project, source=source, status=Status.finished, result=Result.passed)

        child_revision = self.create_revision(repository=project.repository, parents=[revision.sha])

        with mock.patch('changes.listeners.revision_result.create_or_update_revision_result') as mocked:
            create_or_update_revision_result(build.source.revision_sha, build.project_id, propagation_limit=0)

        revision_result = RevisionResult.query.filter(
            RevisionResult.project_id == build.project_id,
            RevisionResult.revision_sha == build.source.revision_sha,
        ).first()

        assert revision_result is not None
        assert revision_result.build == build
        assert revision_result.result is Result.passed

        assert mocked.call_count == 0
