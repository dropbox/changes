from datetime import datetime

from changes.testutils import APITestCase


class TaskIndexTest(APITestCase):
    def test_simple(self):
        task_1 = self.create_task(
            task_name='example',
            date_created=datetime(2013, 9, 19, 22, 15, 24),
        )
        task_2 = self.create_task(
            task_name='example',
            date_created=datetime(2013, 9, 20, 22, 15, 24),
        )

        path = '/api/0/tasks/'

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 2
        assert data[0]['id'] == task_2.id.hex
        assert data[1]['id'] == task_1.id.hex
