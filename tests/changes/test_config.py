from mock import patch

from changes.models import User
from changes.config import db
from changes.testutils import TestCase


class TestDBTransactionTracking(TestCase):

    @patch('logging.warning')
    def test_txn_timing(self, mock_warning):
        with patch('time.time', return_value=10):
            user_emails = list(db.session.query(User.email))

        assert 10 == db.session.info['txn_start_time']

        with patch('time.time', return_value=15):
            db.session.commit()

        assert 'txn_start_time' not in db.session.info
        call_args = mock_warning.call_args[0]
        assert call_args[2] == 5000
