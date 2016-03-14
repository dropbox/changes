from flask import session
from flask.ext.restful import reqparse

from changes.api.base import APIView
from changes.config import db
from changes.models import Build, Comment, User


class BuildCommentIndexAPIView(APIView):
    parser = reqparse.RequestParser()
    parser.add_argument('text', type=unicode, required=True)

    def get(self, build_id):
        build = Build.query.get(build_id)
        if build is None:
            return '', 404

        comments = list(Comment.query.filter(
            Comment.build == build,
        ).order_by(Comment.date_created.desc()))

        return self.respond(comments)

    def post(self, build_id):
        if not session.get('uid'):
            return '', 401

        user = User.query.get(session['uid'])
        if user is None:
            return '', 401

        build = Build.query.get(build_id)
        if build is None:
            return '', 404

        args = self.parser.parse_args()

        # TODO(dcramer): ensure this comment wasnt just created
        comment = Comment(
            build=build,
            user=user,
            text=args.text.strip(),
        )
        db.session.add(comment)

        # TODO(dcramer): this should send out a notification about a new comment

        return self.respond(comment)
