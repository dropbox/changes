from __future__ import absolute_import

from flask.ext.restful import reqparse
from sqlalchemy.orm import joinedload
from datetime import datetime, timedelta

from changes.api.base import APIView
from changes.api.serializer.models.job import JobWithBuildCrumbler
from changes.api.validators.basic import bounded_integer
from changes.constants import Result
from changes.models.job import Job


class InfraFailJobIndexAPIView(APIView):
    """Defines the endpoint for fetching jobs that recently failed for infrastructural reasons."""

    get_parser = reqparse.RequestParser()
    get_parser.add_argument('limit', type=bounded_integer(0, 1000), location='args',
                            default=250)

    def get(self):
        args = self.get_parser.parse_args()

        jobs = Job.query.options(
            joinedload(Job.build, innerjoin=True),
        ).filter(
            Job.result == Result.infra_failed,
            # Only last 24 hours so that a non-empty view can be a matter for concern.
            Job.date_created >= datetime.utcnow() - timedelta(hours=24),
        ).order_by(Job.date_created.desc()
        ).limit(args.limit)

        result = {
            'recent': list(jobs),
        }
        return self.respond(result, serializers={
            Job: JobWithBuildCrumbler(),
        })
