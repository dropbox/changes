from datetime import datetime

from changes.testutils import APITestCase


PATH = '/api/0/messages/'


class AdminMessageIndexTest(APITestCase):
    def test_get_no_messages(self):
        resp = self.client.get(PATH)
        assert resp.status_code == 200
        assert not self.unserialize(resp)

    def test_get_single_message(self):
        test_message = '$ome message with 1234 & <html></html>'
        notifier = self.create_user(email='foobar@example.com')
        self.create_adminmessage(user=notifier,
                                 message=test_message,
                                 date_created=datetime(2015, 1, 19, 22, 15, 22))

        resp = self.client.get(PATH)

        assert resp.status_code == 200
        data = self.unserialize(resp)

        # Confirm the right user in the notification
        assert data['user']['id'] == notifier.id.hex
        assert data['user']['email'] == notifier.email

        # Confirm the right message and other data in the notification
        assert data['message'] == test_message
        assert data['dateCreated'] == '2015-01-19T22:15:22'


class UpdateAdminMessageTest(APITestCase):
    def test_require_admin(self):
        # ensure endpoint requires authentication
        resp = self.client.post(PATH, data={
            'message': 'some message'
        })
        assert resp.status_code == 401

        # ensure endpoint requires admin
        self.login_default()
        resp = self.client.post(PATH, data={
            'message': 'some message'
        })
        assert resp.status_code == 403

    def test_require_message(self):
        self.login_default_admin()
        resp = self.client.post(PATH, data={})
        assert resp.status_code == 400

    def test_message_creation(self):
        test_message = '$ome message with 1234 & <html></html>'

        # test valid params
        user = self.login_default_admin()
        resp = self.client.post(PATH, data={
            'message': test_message
        })
        assert resp.status_code == 200

        data = self.unserialize(resp)
        assert data['message'] == test_message
        assert data['user']['id'] == user.id.hex

    def test_update_message(self):
        user = self.login_default_admin()
        create_date = datetime(2015, 1, 19, 22, 15, 22)
        self.create_adminmessage(user=user,
                                 message='$ome message 1234 & <html></html>',
                                 date_created=create_date)

        # Update existing notification
        second_message = 'second message'
        resp = self.client.post(PATH, data={
            'message': second_message
        })
        assert resp.status_code == 200

        data = self.unserialize(resp)
        assert data['message'] == second_message
        assert data['user']['id'] == user.id.hex

        # Simulate another user clearing notification
        another_user = self.login_default_admin()
        resp = self.client.post(PATH, data={
            'message': ''
        })
        assert resp.status_code == 200

        data = self.unserialize(resp)
        assert not data['message']
        assert data['user']['id'] == another_user.id.hex
