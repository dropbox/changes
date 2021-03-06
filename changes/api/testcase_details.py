from sqlalchemy.orm import subqueryload_all

from changes.artifacts import xunit
from changes.api.base import APIView
from changes.models.log import LogSource
from changes.models.test import TestCase


class TestCaseDetailsAPIView(APIView):
    def get(self, test_id):
        testcase = TestCase.query.options(
            subqueryload_all('artifacts'),
            subqueryload_all('messages')
        ).get(test_id)

        if testcase is None:
            return '', 404

        context = self.serialize(testcase)

        context['message'] = xunit.get_testcase_messages(testcase)

        context['step'] = self.serialize(testcase.step)
        context['artifacts'] = self.serialize(testcase.artifacts)

        # XXX(dcramer): we assume one log per step
        context['logSource'] = self.serialize(LogSource.query.filter(
            LogSource.step_id == testcase.step_id,
        ).first())

        return self.respond(context)
