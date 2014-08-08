from __future__ import absolute_import

from flask.ext.restful import reqparse

from changes.api.base import APIView
from changes.config import db
from changes.db.utils import create_or_update
from changes.models import ProjectOption, Snapshot, SnapshotStatus


class SnapshotDetailsAPIView(APIView):
    parser = reqparse.RequestParser()
    parser.add_argument('status', choices=SnapshotStatus._member_names_)
    parser.add_argument('set_current', type=bool)

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

        if args.status:
            snapshot.status = SnapshotStatus._member_map_[args.status]
        if args.set_current and snapshot.status != SnapshotStatus.active:
            return '{"error": "Cannot set inactive current snapshot"}', 400

        db.session.add(snapshot)
        db.session.commit()

        if args.set_current:
            # TODO(adegtiar): improve logic for picking current snapshot.
            create_or_update(ProjectOption, where={
                'project': snapshot.project,
                'name': 'snapshot.current',
            }, values={
                'value': snapshot.id.hex,
            })

        return self.respond(snapshot)
