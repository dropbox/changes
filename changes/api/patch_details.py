from __future__ import absolute_import

from flask import request, Response

from changes.api.base import APIView
from changes.models import Patch


class PatchDetailsAPIView(APIView):
    def get(self, patch_id):
        patch = Patch.query.get(patch_id)
        if patch is None:
            return '', 404

        if request.args.get('raw'):
            return Response(patch.diff, mimetype='text/plain')

        return self.respond(patch)
