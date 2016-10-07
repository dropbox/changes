from changes.testutils import APITestCase


class BuildTargetMessageIndexTestCase(APITestCase):
    path = '/api/0/builds/{build_id}/targets/{target_id}/messages/'

    def test_correct(self):
        build = self.create_build(self.create_project())
        job = self.create_job(build)
        target = self.create_target(job)
        message1 = self.create_target_message(target, text="Test message")
        message2 = self.create_target_message(target, text="Test message")
        message3 = self.create_target_message(target, text="Test message")

        resp = self.client.get(self.path.format(build_id=build.id.hex, target_id=target.id.hex))
        assert resp.status_code == 200
        data = self.unserialize(resp)

        assert [m['id'] for m in data] == [message1.id.hex, message2.id.hex, message3.id.hex]
