from changes.constants import Cause, Result, Status
from changes.models import Build, Job
from changes.testutils import APITestCase, SAMPLE_DIFF


class DiffBuildRetryTest(APITestCase):
    def test_simple(self):
        diff_id = 123
        project = self.create_project()
        patch = self.create_patch(
            repository_id=project.repository_id,
            diff=SAMPLE_DIFF
            )
        source = self.create_source(
            project,
            patch=patch,
            )
        diff = self.create_diff(diff_id, source=source)
        build = self.create_build(
            project=project,
            source=source,
            status=Status.finished,
            result=Result.failed
            )
        job = self.create_job(build=build)

        self.create_plan(project)

        path = '/api/0/phabricator_diffs/{0}/retry/'.format(diff_id)
        resp = self.client.post(path, follow_redirects=True)

        assert resp.status_code == 200

        data = self.unserialize(resp)

        assert len(data) == 1

        new_build = Build.query.get(data[0]['id'])

        assert new_build.id != build.id
        assert new_build.collection_id != build.collection_id
        assert new_build.project_id == project.id
        assert new_build.cause == Cause.retry
        assert new_build.author_id == build.author_id
        assert new_build.source_id == build.source_id
        assert new_build.label == build.label
        assert new_build.message == build.message
        assert new_build.target == build.target

        jobs = list(Job.query.filter(
            Job.build_id == new_build.id,
        ))

        assert len(jobs) == 1

        new_job = jobs[0]
        assert new_job.id != job.id

    def test_simple_passed(self):
        diff_id = 123
        project = self.create_project()
        patch = self.create_patch(
            repository_id=project.repository_id,
            diff=SAMPLE_DIFF
            )
        source = self.create_source(
            project,
            patch=patch,
            )
        diff = self.create_diff(diff_id, source=source)
        build = self.create_build(
            project=project,
            source=source,
            status=Status.finished,
            result=Result.passed
            )
        job = self.create_job(build=build)

        self.create_plan(project)

        path = '/api/0/phabricator_diffs/{0}/retry/'.format(diff_id)
        resp = self.client.post(path, follow_redirects=True)

        assert resp.status_code == 200

        data = self.unserialize(resp)

        assert len(data) == 0

    def test_simple_in_progress(self):
        diff_id = 123
        project = self.create_project()
        patch = self.create_patch(
            repository_id=project.repository_id,
            diff=SAMPLE_DIFF
            )
        source = self.create_source(
            project,
            patch=patch,
            )
        diff = self.create_diff(diff_id, source=source)
        build = self.create_build(
            project=project,
            source=source,
            status=Status.in_progress,
            result=Result.failed
            )
        job = self.create_job(build=build)

        self.create_plan(project)

        path = '/api/0/phabricator_diffs/{0}/retry/'.format(diff_id)
        resp = self.client.post(path, follow_redirects=True)

        assert resp.status_code == 200

        data = self.unserialize(resp)

        assert len(data) == 0

    def test_multiple_builds_same_project(self):
        diff_id = 123
        project = self.create_project()
        patch = self.create_patch(
            repository_id=project.repository_id,
            diff=SAMPLE_DIFF
            )
        source = self.create_source(
            project,
            patch=patch,
            )
        diff = self.create_diff(diff_id, source=source)
        old_build = self.create_build(
            project=project,
            source=source
            )
        build = self.create_build(
            project=project,
            source=source,
            status=Status.finished,
            result=Result.failed
            )
        job = self.create_job(build=build)

        self.create_plan(project)

        path = '/api/0/phabricator_diffs/{0}/retry/'.format(diff_id)
        resp = self.client.post(path, follow_redirects=True)

        assert resp.status_code == 200

        data = self.unserialize(resp)

        assert len(data) == 1

        new_build = Build.query.get(data[0]['id'])

        assert new_build.id != build.id
        assert new_build.collection_id != build.collection_id
        assert new_build.project_id == project.id
        assert new_build.cause == Cause.retry
        assert new_build.author_id == build.author_id
        assert new_build.source_id == build.source_id
        assert new_build.label == build.label
        assert new_build.message == build.message
        assert new_build.target == build.target

        jobs = list(Job.query.filter(
            Job.build_id == new_build.id,
        ))

        assert len(jobs) == 1

        new_job = jobs[0]
        assert new_job.id != job.id

    def test_multiple_builds_different_projects(self):
        diff_id = 123
        project = self.create_project()
        patch = self.create_patch(
            repository_id=project.repository_id,
            diff=SAMPLE_DIFF
            )
        source = self.create_source(
            project,
            patch=patch,
            )
        diff = self.create_diff(diff_id, source=source)
        old_build = self.create_build(
            project=project,
            source=source
            )
        build = self.create_build(
            project=project,
            source=source,
            status=Status.finished,
            result=Result.failed
            )
        job = self.create_job(build=build)

        self.create_plan(project)

        project2 = self.create_project(
            repository=project.repository,
            name="project 2"
            )

        build2 = self.create_build(
            project=project2,
            source=source,
            status=Status.finished,
            result=Result.passed
            )

        job2 = self.create_job(build=build2)

        self.create_plan(project2)

        path = '/api/0/phabricator_diffs/{0}/retry/'.format(diff_id)
        resp = self.client.post(path, follow_redirects=True)

        assert resp.status_code == 200

        data = self.unserialize(resp)

        assert len(data) == 1

        new_build = Build.query.get(data[0]['id'])

        assert new_build.id != build.id
        assert new_build.collection_id != build.collection_id
        assert new_build.project_id == project.id
        assert new_build.cause == Cause.retry
        assert new_build.author_id == build.author_id
        assert new_build.source_id == build.source_id
        assert new_build.label == build.label
        assert new_build.message == build.message
        assert new_build.target == build.target

        jobs = list(Job.query.filter(
            Job.build_id == new_build.id,
        ))

        assert len(jobs) == 1

        new_job = jobs[0]
        assert new_job.id != job.id

    def test_multiple_builds_different_projects_all_failed(self):
        diff_id = 123
        project = self.create_project()
        patch = self.create_patch(
            repository_id=project.repository_id,
            diff=SAMPLE_DIFF
            )
        source = self.create_source(
            project,
            patch=patch,
            )
        diff = self.create_diff(diff_id, source=source)
        old_build = self.create_build(
            project=project,
            source=source
            )
        build = self.create_build(
            project=project,
            source=source,
            status=Status.finished,
            result=Result.failed
            )
        job = self.create_job(build=build)

        self.create_plan(project)

        project2 = self.create_project(
            repository=project.repository,
            name="project 2"
            )

        build2 = self.create_build(
            project=project2,
            source=source,
            status=Status.finished,
            result=Result.failed
            )

        job2 = self.create_job(build=build2)

        self.create_plan(project2)

        path = '/api/0/phabricator_diffs/{0}/retry/'.format(diff_id)
        resp = self.client.post(path, follow_redirects=True)

        assert resp.status_code == 200

        data = self.unserialize(resp)

        assert len(data) == 2

        data = [Build.query.get(x['id']) for x in data]

        new_build = [x for x in data if x.project_id == build.project_id][0]

        assert new_build.id != build.id
        assert new_build.collection_id != build.collection_id
        assert new_build.cause == Cause.retry
        assert new_build.author_id == build.author_id
        assert new_build.source_id == build.source_id
        assert new_build.label == build.label
        assert new_build.message == build.message
        assert new_build.target == build.target

        jobs = list(Job.query.filter(
            Job.build_id == new_build.id,
        ))

        new_job = jobs[0]
        assert new_job.id != job.id

        new_build2 = [x for x in data if x.project_id == build2.project_id][0]

        assert new_build2.id != build2.id
        assert new_build2.collection_id != build2.collection_id
        assert new_build2.cause == Cause.retry
        assert new_build2.author_id == build2.author_id
        assert new_build2.source_id == build2.source_id
        assert new_build2.label == build2.label
        assert new_build2.message == build2.message
        assert new_build2.target == build2.target

        jobs = list(Job.query.filter(
            Job.build_id == new_build2.id,
        ))

        assert len(jobs) == 1

        new_job = jobs[0]
        assert new_job.id != job2.id
