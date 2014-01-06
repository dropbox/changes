from flask import Response
from sqlalchemy.orm import joinedload

from changes.api.base import APIView
from changes.api.build_index import create_build
from changes.constants import Cause
from changes.models import Build


class BuildRetryAPIView(APIView):
    def post(self, build_id):
        build = Build.query.options(
            joinedload(Build.project),
            joinedload(Build.author),
        ).get(build_id)
        if build is None:
            return Response(status=404)

        new_build = create_build(
            project=build.project,
            label=build.label,
            target=build.target,
            message=build.message,
            author=build.author,
            patch=build.patch,
            source=build.source,
            cause=Cause.retry,
        )

        return '', 302, {'Location': '/api/0/builds/{0}/'.format(new_build.id.hex)}
