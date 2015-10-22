import json

from changes.config import db
from changes.models import Build
from changes.api.base import APIView, error

from flask.ext.restful import reqparse


class BuildTagAPIView(APIView):
    post_parser = reqparse.RequestParser()
    post_parser.add_argument('tags', type=lambda x: json.loads(x), required=True)

    def get(self, build_id):
        """ Retrieve all tags associated with a build. """

        build = Build.query.get(build_id)

        if build is None:
            return self.respond({}, status_code=404)

        tags = build.tags if build.tags else []
        return self.respond({'tags': tags})

    def post(self, build_id):
        """ Set tags associated with a build. """

        args = self.post_parser.parse_args()

        if args.tags and (not all(len(tag) <= 16 for tag in args.tags)):
            return error('Tags must be 16 characters or less.')

        build = Build.query.get(build_id)

        # if the build is not in findable in db after we just fetched
        # it to put on the page, there's something wrong.
        if build is None:
            return self.respond({}, status_code=404)

        build.tags = args.tags

        db.session.add(build)
        db.session.commit()

        return self.respond({})
