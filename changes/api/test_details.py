from flask import Response

from changes.api.base import APIView
from changes.api.serializer import Serializer
from changes.constants import Status
from changes.models import Build, Author, TestCase, TestSuite

NUM_PREVIOUS_RUNS = 50


class TestCaseWithBuildSerializer(Serializer):
    def serialize(self, instance):
        return {
            'id': instance.id.hex,
            'name': instance.name,
            'package': instance.package,
            'result': instance.result,
            'duration': instance.duration,
            'message': instance.message,
            'link': '/tests/%s/' % (instance.id.hex,),
            'dateCreated': instance.date_created,
            'build': instance.build,
        }


class TestDetailsAPIView(APIView):
    def get(self, test_id):
        test = TestCase.query.get(test_id)
        if test is None:
            return Response(status=404)

        # find other builds this test has run in
        # TODO(dcramer): ideally this would only query for builds which
        # are previous in vcs tree (not based on simply date created)
        previous_runs = TestCase.query.join(Build, TestSuite).outerjoin(Author).filter(
            TestSuite.name_sha == test.suite.name_sha,
            TestCase.name_sha == test.name_sha,
            Build.date_created < test.build.date_created,
            Build.status == Status.finished,
            TestCase.id != test.id,
        ).order_by(Build.date_created.desc())[:NUM_PREVIOUS_RUNS]

        if len(previous_runs) < NUM_PREVIOUS_RUNS:
            try:
                first_run = previous_runs[0]
            except IndexError:
                first_run = None
        else:
            first_run = TestCase.query.join(Build, TestSuite).outerjoin(Author).filter(
                TestSuite.name_sha == test.suite.name_sha,
                TestCase.name_sha == test.name_sha,
                Build.status == Status.finished,
            ).order_by(Build.date_created.asc()).first()

        # if we end up just discovering ourself, then we must be the first run
        if first_run and first_run.id == test.id:
            first_run = None

        extended_serializers = {
            TestCase: TestCaseWithBuildSerializer(),
        }

        context = {
            'build': test.build,
            'test': test,
            'previousRuns': self.serialize(previous_runs, extended_serializers),
            'firstRun': self.serialize(first_run, extended_serializers),
        }

        return self.respond(context)

    def get_stream_channels(self, test_id):
        return [
            'tests:*:*:{0}'.format(test_id),
        ]
