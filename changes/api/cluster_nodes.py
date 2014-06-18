from __future__ import absolute_import

from datetime import datetime, timedelta
from flask.ext.restful import reqparse

from changes.api.base import APIView
from changes.models import Cluster, JobStep, Node


class ClusterNodesAPIView(APIView):
    parser = reqparse.RequestParser()
    parser.add_argument('since', type=int, location='args')

    def get(self, cluster_id):
        cluster = Cluster.query.get(cluster_id)
        if cluster is None:
            return '', 404

        queryset = Node.query.filter(
            Node.clusters.contains(cluster),
        ).order_by(Node.label.asc())

        args = self.parser.parse_args()
        if args.since:
            cutoff = datetime.utcnow() - timedelta(days=args.since)

            queryset = queryset.join(
                JobStep, JobStep.node_id == Node.id,
            ).filter(
                JobStep.date_created > cutoff,
            ).group_by(Node)

        return self.paginate(queryset)
