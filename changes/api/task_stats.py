from collections import defaultdict

from changes.api.base import APIView
from changes.constants import Status
from changes.models.task import Task


class TaskStatsAPIView(APIView):
    def get(self):
        """
        GET method that returns aggregated data regarding tasks in progress.

        Returns:
            {
                '[task name]': {
                    '[task status]': [info],
                    ...
                    'all': [info],
                }
                'all': {
                    '[task status]': [info],
                    ...
                    'all': [info],
                }
            }

            where [info] is:
            {
                'count': ...,
                'max_retries': ...,
                'max_retries_id': ...,
                'oldest_created_time': ...,
                'oldest_created_id': ...,
                'oldest_modified_time': ...,
                'oldest_modified_id': ...,
            }
        """

        def aggregate(task, agg):
            if agg['count'] is None:
                agg['count'] = 0
            agg['count'] += 1
            if agg['max_retries'] is None or task.num_retries > agg['max_retries']:
                agg['max_retries'] = task.num_retries
                agg['max_retries_id'] = task.id
            if agg['oldest_created_time'] is None or task.date_created < agg['oldest_created_time']:
                agg['oldest_created_time'] = task.date_created
                agg['oldest_created_id'] = task.id
            if agg['oldest_modified_time'] is None or task.date_modified < agg['oldest_modified_time']:
                agg['oldest_modified_time'] = task.date_modified
                agg['oldest_modified_id'] = task.id

        tasks = Task.query.filter(Task.status != Status.finished)

        #       [task name]         [task status]       [stat]
        stats = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: None)))

        for task in tasks:
            for name in [task.task_name, 'all']:
                for status in [task.status.name, 'all']:
                    aggregate(task, stats[name][status])

        return self.respond(stats)
