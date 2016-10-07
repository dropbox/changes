from changes.testutils import APITestCase


class BuildMessageIndexTestCase(APITestCase):
    path = '/api/0/builds/{build_id}/messages/'

    def test_correct(self):
        build = self.create_build(self.create_project())
        message1 = self.create_build_message(build, text="Test message")
        message2 = self.create_build_message(build, text="Test message")
        message3 = self.create_build_message(build, text="Test message")

        resp = self.client.get(self.path.format(build_id=build.id.hex))
        assert resp.status_code == 200
        data = self.unserialize(resp)

        assert [m['id'] for m in data] == [message1.id.hex, message2.id.hex, message3.id.hex]
