from flask import Response

from changes.api.base import APIView
from changes.models import Test


class TestDetailsAPIView(APIView):
    def get(self, test_id):
        test = Test.query.get(test_id)
        if test is None:
            return Response(status=404)

        context = {
            'build': test.build,
            'test': test,
        }

        return self.respond(context)

    def get_stream_channels(self, test_id):
        return [
            'tests:*:*:{0}'.format(test_id),
        ]
