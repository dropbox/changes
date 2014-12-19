import uuid

from sqlalchemy.orm import joinedload

from changes.api.base import APIView
from changes.api.build_index import create_build
from changes.constants import Cause
from changes.models import Build


class BuildRetryAPIView(APIView):
    def post(self, build_id):
        build = Build.query.options(
            joinedload('project', innerjoin=True),
            joinedload('author'),
            joinedload('source').joinedload('revision'),
        ).get(build_id)
        if build is None:
            return '', 404

        collection_id = uuid.uuid4()
        new_build = create_build(
            project=build.project,
            collection_id=collection_id,
            label=build.label,
            target=build.target,
            message=build.message,
            author=build.author,
            source=build.source,
            cause=Cause.retry,
        )

        return '', 302, {'Location': '/api/0/builds/{0}/'.format(new_build.id.hex)}
