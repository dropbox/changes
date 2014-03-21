from __future__ import absolute_import

from changes.api.base import APIView
from changes.models import Task


class TaskDetailsAPIView(APIView):
    def _collect_children(self, task):
        children = Task.query.filter(
            Task.parent_id == task.task_id,
        )
        results = []
        for child in children:
            child_data = self.serialize(child)
            child_data['children'] = self._collect_children(child)
            results.append(child_data)

        return results

    def get(self, task_id):
        task = Task.query.get(task_id)
        if task is None:
            return '', 404

        context = self.serialize(task)
        context['children'] = self._collect_children(task)

        return self.respond(context)
