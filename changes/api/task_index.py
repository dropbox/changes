from __future__ import absolute_import

from changes.api.base import APIView
from changes.models import Task


class TaskIndexAPIView(APIView):
    def get(self):
        queryset = Task.query.order_by(Task.date_created.desc())

        return self.paginate(queryset)
