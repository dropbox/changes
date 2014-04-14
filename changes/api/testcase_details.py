from changes.api.base import APIView
from changes.models import TestCase


class TestCaseDetailsAPIView(APIView):
    def get(self, test_id):
        testcase = TestCase.query.get(test_id)
        if testcase is None:
            return '', 404

        context = self.serialize(testcase)
        context['message'] = testcase.message

        return self.respond(context)
