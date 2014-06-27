from changes.api.base import APIView
from changes.models import LogSource, TestCase


class TestCaseDetailsAPIView(APIView):
    def get(self, test_id):
        testcase = TestCase.query.get(test_id)
        if testcase is None:
            return '', 404

        context = self.serialize(testcase)
        context['message'] = testcase.message
        context['step'] = self.serialize(testcase.step)

        # XXX(dcramer): we assume one log per step
        context['logSource'] = self.serialize(LogSource.query.filter(
            LogSource.step_id == testcase.step_id,
        ).first())

        return self.respond(context)
