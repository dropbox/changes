from __future__ import absolute_import

from flask_restful.reqparse import RequestParser
from sqlalchemy.orm import joinedload

from changes.api.base import APIView
from changes.api.serializer.models.snapshot import SnapshotWithImagesSerializer
from changes.models import Snapshot, SnapshotStatus

STATE_CHOICES = ('', 'valid', 'invalid')

SORT_CHOICES = ('name', 'date')


class SnapshotIndexAPIView(APIView):
    get_parser = RequestParser()
    get_parser.add_argument('state', type=unicode, location='args',
                            choices=STATE_CHOICES, default='valid')

    def get(self):
        args = self.get_parser.parse_args()

        queryset = Snapshot.query.options(
            joinedload('source').joinedload('revision'),
        ).order_by(
            Snapshot.date_created.desc(),
        )

        if args.state == 'valid':
            queryset = queryset.filter(
                Snapshot.status != SnapshotStatus.invalidated,
            )
        elif args.state == 'invalid':
            queryset = queryset.filter(
                Snapshot.status == SnapshotStatus.invalidated,
            )

        return self.paginate(queryset, serializers={
            Snapshot: SnapshotWithImagesSerializer(),
        })
