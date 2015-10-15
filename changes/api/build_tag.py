import json

from changes.config import db
from changes.models import Build
from changes.api.base import APIView, error

from flask.ext.restful import reqparse


class BuildTagAPIView(APIView):
    post_parser = reqparse.RequestParser()
    post_parser.add_argument('tags', type=str, required=True)

    def get(self, build_id):
        """ Retrieve all tags associated with a build. """

        build = Build.query.get(build_id)

        if build is None:
            return self.respond({}, status_code=404)

        tags = build.tags if build.tags else []
        return self.respond({'tags': build.tags})

    def post(self, build_id):
        """ Set tags associated with a build. """

        args = self.post_parser.parse_args()
        try:
            tags = json.loads(args.tags)
        except ValueError as err:
            return error(err.message, ['tags'])

        build = Build.query.get(build_id)

        # if the build is not in findable in db after we just fetched
        # it to put on the page, there's something wrong.
        if build is None:
            return self.respond({}, status_code=404)

        build.tags = tags

        db.session.add(build)
        db.session.commit()

        return self.respond({})
