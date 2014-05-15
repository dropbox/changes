from mock import Mock, patch

from flask import current_app

from changes.jobs.signals import fire_signal, run_event_listener
from changes.testutils import TestCase


class SignalTestBase(TestCase):
    def setUp(self):
        super(SignalTestBase, self).setUp()
        self.original_listeners = current_app.config['EVENT_LISTENERS']
        current_app.config['EVENT_LISTENERS'] = (
            ('mock.Mock', 'test.signal'),
        )

    def tearDown(self):
        current_app.config['EVENT_LISTENERS'] = self.original_listeners
        super(SignalTestBase, self).tearDown()


class FireSignalTest(SignalTestBase):
    @patch('changes.jobs.signals.run_event_listener')
    def test_simple(self, mock_run_event_listener):
        fire_signal(signal='test.signal', kwargs={'foo': 'bar'})

        mock_run_event_listener.delay.assert_any_call(
            listener='mock.Mock',
            signal='test.signal',
            kwargs={'foo': 'bar'},
        )


class RunEventListenerTest(SignalTestBase):
    @patch('changes.jobs.signals.import_string')
    def test_simple(self, mock_import_string):
        mock_listener = Mock()
        mock_import_string.return_value = mock_listener

        run_event_listener(
            listener='mock.Mock',
            signal='test.signal',
            kwargs={'foo': 'bar'},
        )

        mock_import_string.assert_called_once_with('mock.Mock')

        mock_listener.assert_called_once_with(foo='bar')
