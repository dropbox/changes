from __future__ import absolute_import

from changes.api.base import APIView
from changes.models import Cluster


class ClusterIndexAPIView(APIView):
    def get(self):
        queryset = Cluster.query.order_by(Cluster.label.asc())

        return self.paginate(queryset)
