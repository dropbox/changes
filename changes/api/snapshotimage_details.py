from __future__ import absolute_import

from flask.ext.restful import reqparse

from changes.api.base import APIView
from changes.models.snapshot import SnapshotImage, SnapshotStatus


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
            image.change_status(SnapshotStatus[args.status])

        return self.respond(image)
