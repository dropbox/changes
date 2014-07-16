from __future__ import absolute_import

from flask.ext.restful import reqparse

from changes.api.base import APIView
from changes.config import db
from changes.models import Snapshot, SnapshotStatus


class SnapshotDetailsAPIView(APIView):
    parser = reqparse.RequestParser()
    parser.add_argument('url', type=unicode)
    parser.add_argument('status', choices=SnapshotStatus._member_names_)

    def get(self, snapshot_id):
        snapshot = Snapshot.query.get(snapshot_id)
        if snapshot is None:
            return '', 404

        return self.respond(snapshot)

    def post(self, snapshot_id):
        snapshot = Snapshot.query.get(snapshot_id)
        if snapshot is None:
            return '', 404

        args = self.parser.parse_args()

        if args.url:
            snapshot.url = args.url
        if args.status:
            snapshot.status = SnapshotStatus._member_map_[args.status]

        db.session.add(snapshot)
        db.session.commit()

        return self.respond(snapshot)
