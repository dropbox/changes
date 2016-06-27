from xml.sax import saxutils
from sqlalchemy.orm import subqueryload_all

from flask import current_app

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

        context['message'] = testcase.message or ''
        message_limit = current_app.config.get('TEST_MESSAGE_MAX_LEN')
        for m in testcase.messages:
            if context['message']:
                context['message'] += '\n\n'
            context['message'] +=\
                (' ' + m.label + ' ').center(78, '=') + '\n' +\
                xunit.truncate_message(saxutils.unescape(m.get_message()), message_limit)

        context['step'] = self.serialize(testcase.step)
        context['artifacts'] = self.serialize(testcase.artifacts)

        # XXX(dcramer): we assume one log per step
        context['logSource'] = self.serialize(LogSource.query.filter(
            LogSource.step_id == testcase.step_id,
        ).first())

        return self.respond(context)
