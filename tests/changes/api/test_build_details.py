from datetime import datetime

from changes.config import db
from changes.constants import Status
from changes.models import (
    Build, BuildPriority, Event, FailureReason, ItemStat, TestCase
)
from changes.testutils import APITestCase, TestCase as BaseTestCase
from changes.api.build_details import find_changed_tests


class FindChangedTestsTest(BaseTestCase):
    def test_simple(self):
        project = self.create_project()

        previous_build = self.create_build(project)
        previous_job = self.create_job(previous_build)

        changed_test = TestCase(
            job=previous_job,
            project=previous_job.project,
            name='unchanged test',
        )
        removed_test = TestCase(
            job=previous_job,
            project=previous_job.project,
            name='removed test',
        )
        db.session.add(removed_test)
        db.session.add(changed_test)

        current_build = self.create_build(project)
        current_job = self.create_job(current_build)
        added_test = TestCase(
            job=current_job,
            project=current_job.project,
            name='added test',
        )

        db.session.add(added_test)
        db.session.add(TestCase(
            job=current_job,
            project=current_job.project,
            name='unchanged test',
        ))
        db.session.commit()

        results = find_changed_tests(current_build, previous_build)

        assert results['total'] == 2

        assert ('-', removed_test) in results['changes']
        assert ('+', added_test) in results['changes']

        assert len(results['changes']) == 2


class BuildDetailsTest(APITestCase):
    def test_simple(self):
        project = self.create_project()
        previous_build = self.create_build(
            project, date_created=datetime(2013, 9, 19, 22, 15, 23),
            status=Status.finished)
        build = self.create_build(
            project, date_created=datetime(2013, 9, 19, 22, 15, 24))
        job1 = self.create_job(build)
        job2 = self.create_job(build)
        phase = self.create_jobphase(job1)
        step = self.create_jobstep(phase)
        db.session.add(Event(
            item_id=build.id,
            type='green_build_notification',
        ))
        db.session.add(ItemStat(
            item_id=build.id,
            name='test_failures',
            value=2,
        ))
        db.session.add(FailureReason(
            project_id=project.id,
            build_id=build.id,
            job_id=job1.id,
            step_id=step.id,
            reason='test_failures'
        ))
        db.session.commit()

        path = '/api/0/builds/{0}/'.format(build.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == build.id.hex
        assert len(data['jobs']) == 2
        assert data['jobs'][0]['id'] == job1.id.hex
        assert data['jobs'][1]['id'] == job2.id.hex
        assert len(data['previousRuns']) == 1
        assert data['previousRuns'][0]['id'] == previous_build.id.hex
        assert data['seenBy'] == []
        assert data['testFailures']['total'] == 0
        assert data['testFailures']['tests'] == []
        assert data['testChanges'] == []
        assert len(data['events']) == 1
        assert len(data['failures']) == 1
        assert data['failures'][0] == {
            'id': 'test_failures',
            'reason': 'There were <a href="http://example.com/projects/{0}/builds/{1}/tests/?result=failed">2 failing tests</a>.'.format(
                project.slug,
                build.id.hex,
            ),
            'count': 1,
        }

    def test_last_parent_revision_build(self):
        project = self.create_project()

        parent_revision_build = self.create_build(
            project, status=Status.finished)
        parent_sha = parent_revision_build.source.revision_sha

        revision = self.create_revision(repository_id=project.repository_id,
                                        parents=[parent_sha],)
        source = self.create_source(project,
                                    revision_sha=revision.sha)

        build = self.create_build(project, source=source)
        path = '/api/0/builds/{0}/'.format(build.id.hex)
        resp = self.client.get(path)
        data = self.unserialize(resp)

        assert data['parentRevisionBuild']['source']['revision']['sha'] == parent_sha

    def test_parent_revision_has_no_build(self):
        project = self.create_project()
        revision = self.create_revision(repository_id=project.repository_id,
                                        parents=['random-sha-with-no-build-for-it'],)
        source = self.create_source(project,
                                    revision_sha=revision.sha)

        build = self.create_build(project, source=source)
        path = '/api/0/builds/{0}/'.format(build.id.hex)
        resp = self.client.get(path)
        data = self.unserialize(resp)

        assert data['parentRevisionBuild'] is None


class BuildUpdateTest(APITestCase):
    def test_simple(self):
        project = self.create_project()
        build = self.create_build(
            project, priority=BuildPriority.default)

        path = '/api/0/builds/{0}/'.format(build.id.hex)

        resp = self.client.post(path, data={'priority': 'high'})
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == build.id.hex

        db.session.expire_all()

        build = Build.query.get(build.id)
        assert build.priority == BuildPriority.high
