from __future__ import absolute_import, division, unicode_literals

from sqlalchemy.orm import joinedload
from uuid import UUID

from changes.api.base import APIView
from changes.api.auth import get_current_user
from changes.models import Author, Build


class AuthorBuildIndexAPIView(APIView):
    def _get_author(self, author_id):
        if author_id == 'me':
            user = get_current_user()
            if user is None:
                return None

            return Author.query.filter_by(email=user.email).first()
        try:
            author_id = UUID(author_id)
        except ValueError:
            return None
        return Author.query.get(author_id)

    def get(self, author_id):
        if author_id == 'me' and not get_current_user():
            return '', 401

        author = self._get_author(author_id)
        if not author:
            return '', 404

        queryset = Build.query.options(
            joinedload('project'),
            joinedload('author'),
            joinedload('source').joinedload('revision'),
        ).filter(
            Build.author_id == author.id,
        ).order_by(Build.date_created.desc(), Build.date_started.desc())

        return self.paginate(queryset)

    def get_stream_channels(self, author_id):
        author = self._get_author(author_id)
        if not author:
            return []
        return ['authors:{0}:builds'.format(author.id.hex)]
