from __future__ import absolute_import

from flask.ext.restful import reqparse

from changes.api.base import APIView
from changes.config import db
from changes.models import SnapshotImage, SnapshotStatus


class SnapshotImageDetailsAPIView(APIView):
    parser = reqparse.RequestParser()
    parser.add_argument('status', choices=SnapshotStatus._member_names_)

    def get(self, image_id):
        image = SnapshotImage.query.get(image_id)
        if image is None:
            return '', 404

        return self.respond(image)

    def post(self, image_id):
        image = SnapshotImage.query.get(image_id)
        if image is None:
            return '', 404

        args = self.parser.parse_args()

        if args.status:
            image.status = SnapshotStatus[args.status]

        db.session.add(image)
        db.session.flush()

        if image.status == SnapshotStatus.active:
            snapshot = image.snapshot
            inactive_image_query = SnapshotImage.query.filter(
                SnapshotImage.status != SnapshotStatus.active,
                SnapshotImage.snapshot_id == snapshot.id,
            ).exists()
            if not db.session.query(inactive_image_query).scalar():
                snapshot.status = SnapshotStatus.active
                db.session.add(snapshot)

        db.session.commit()

        return self.respond(image)
