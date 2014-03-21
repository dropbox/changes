from __future__ import absolute_import

from uuid import uuid4

from changes.testutils import APITestCase


class TaskDetailsTest(APITestCase):
    def test_simple(self):
        task = self.create_task(
            task_name='example',
            task_id=uuid4(),
        )
        child_1 = self.create_task(
            task_name='example',
            task_id=uuid4(),
            parent_id=task.task_id,
        )
        child_1_1 = self.create_task(
            task_name='example',
            task_id=uuid4(),
            parent_id=child_1.task_id,
        )
        child_2 = self.create_task(
            task_name='example',
            task_id=uuid4(),
            parent_id=task.task_id,
        )

        path = '/api/0/tasks/{0}/'.format(task.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == task.id.hex
        assert len(data['children']) == 2
