from datetime import datetime

from changes.api.serializer import serialize
from changes.api.serializer.models.testcase import (
    TestCaseWithJobCrumbler, TestCaseWithOriginCrumbler, GeneralizedTestCase
)
from changes.constants import Result
from changes.testutils import TestCase


class TestCaseCrumblerTestCase(TestCase):
    def test_simple(self):
        project = self.create_project()
        build = self.create_build(project=project)
        job = self.create_job(build=build)
        testcase = self.create_test(
            package='test.group.ClassName',
            name='test_foo',
            job=job,
            duration=134,
            result=Result.failed,
            date_created=datetime(2013, 9, 19, 22, 15, 22),
            reruns=1,
        )
        result = serialize(testcase)
        assert result['id'] == str(testcase.id.hex)
        assert result['job']['id'] == str(job.id.hex)
        assert result['project']['id'] == str(project.id.hex)
        assert result['shortName'] == 'test_foo'
        assert result['name'] == 'test_foo'
        assert result['package'] == 'test.group.ClassName'
        assert result['dateCreated'] == '2013-09-19T22:15:22'
        assert result['result']['id'] == 'failed'
        assert result['duration'] == 134
        assert result['numRetries'] == 1

    def test_implicit_package(self):
        project = self.create_project()
        build = self.create_build(project=project)
        job = self.create_job(build=build)
        testcase = self.create_test(
            name='test.group.ClassName.test_foo',
            package=None,
            job=job,
        )

        result = serialize(testcase)

        assert result['shortName'] == 'test_foo'
        assert result['name'] == 'test.group.ClassName.test_foo'
        assert result['package'] == 'test.group.ClassName'

    def test_implicit_package_only_name(self):
        project = self.create_project()
        build = self.create_build(project=project)
        job = self.create_job(build=build)
        testcase = self.create_test(
            name='test_foo',
            package=None,
            job=job
        )
        result = serialize(testcase)
        assert result['shortName'] == 'test_foo'
        assert result['name'] == 'test_foo'
        assert result['package'] is None


class TestCaseWithJobCrumblerTestCase(TestCase):
    def test_simple(self):
        from changes.models import TestCase

        project = self.create_project()
        build = self.create_build(project=project)
        job = self.create_job(build=build)
        testcase = self.create_test(
            job=job,
        )
        result = serialize(testcase, {TestCase: TestCaseWithJobCrumbler()})
        assert result['job']['id'] == str(job.id.hex)


class TestCaseWithOriginCrumblerTestCase(TestCase):
    def test_simple(self):
        from changes.models import TestCase

        project = self.create_project()
        build = self.create_build(project=project)
        job = self.create_job(build=build)
        testcase = self.create_test(
            job=job,
        )

        result = serialize(testcase, {TestCase: TestCaseWithOriginCrumbler()})
        assert result['origin'] is None

        testcase.origin = 'foobar'
        result = serialize(testcase, {TestCase: TestCaseWithOriginCrumbler()})
        assert result['origin'] == 'foobar'


class GeneralizedTestCaseCrumblerTestCase(TestCase):
    def test_simple(self):
        from changes.models import TestCase

        project = self.create_project()
        build = self.create_build(project=project)
        job = self.create_job(build=build)
        testcase = self.create_test(
            job=job,
            package='test.group.ClassName',
            name='test_foo',
            duration=43,
        )
        result = serialize(testcase, {TestCase: GeneralizedTestCase()})
        assert result['hash'] == testcase.name_sha
        assert result['project']['id'] == str(project.id.hex)
        assert result['shortName'] == testcase.short_name
        assert result['name'] == testcase.name
        assert result['package'] == testcase.package
        assert result['duration'] == testcase.duration
