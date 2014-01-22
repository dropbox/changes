from flask import session

from changes.api.base import APIView
from changes.db.utils import try_create
from changes.models import Build, BuildSeen


class BuildMarkSeenAPIView(APIView):
    def post(self, build_id):
        build = Build.query.get(build_id)
        if build is None:
            return '', 404

        if not session.get('uid'):
            return '', 401

        try_create(BuildSeen, where={
            'build_id': build.id,
            'user_id': session['uid'],
        })

        return '', 200
