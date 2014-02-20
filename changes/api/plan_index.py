from __future__ import absolute_import, division, unicode_literals

from changes.api.base import APIView
from changes.models import Plan


class PlanIndexAPIView(APIView):
    def get(self):
        queryset = Plan.query.order_by(Plan.label.asc())
        return self.paginate(queryset)
