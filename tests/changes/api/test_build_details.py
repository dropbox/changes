from datetime import datetime

from changes.config import db
from changes.constants import Status
from changes.models import TestCase
from changes.testutils import APITestCase, TestCase as BaseTestCase
from changes.api.build_details import find_changed_tests


class FindChangedTestsTest(BaseTestCase):
    def test_simple(self):
        previous_build = self.create_build(self.project)
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

        current_build = self.create_build(self.project)
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
        results = find_changed_tests(current_build, previous_build)

        assert results['total'] == 2

        assert ('-', removed_test) in results['changes']
        assert ('+', added_test) in results['changes']

        assert len(results['changes']) == 2


class BuildDetailsTest(APITestCase):
    def test_simple(self):
        previous_build = self.create_build(
            self.project, date_created=datetime(2013, 9, 19, 22, 15, 23),
            status=Status.finished)
        build = self.create_build(
            self.project, date_created=datetime(2013, 9, 19, 22, 15, 24))
        job1 = self.create_job(build)
        job2 = self.create_job(build)

        path = '/api/0/builds/{0}/'.format(build.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['build']['id'] == build.id.hex
        assert data['project']['id'] == self.project.id.hex
        assert len(data['jobs']) == 2
        assert data['jobs'][0]['id'] == job1.id.hex
        assert data['jobs'][1]['id'] == job2.id.hex
        assert len(data['previousRuns']) == 1
        assert data['previousRuns'][0]['id'] == previous_build.id.hex
        assert data['seenBy'] == []
        assert data['testFailures']['total'] == 0
        assert data['testFailures']['testGroups'] == []
        assert data['testChanges'] == []
