from __future__ import absolute_import, division, unicode_literals

from sqlalchemy import or_
from sqlalchemy.orm import joinedload
from uuid import UUID

from changes.api.base import APIView
from changes.api.auth import get_current_user
from changes.models import Author, Build


class AuthorBuildIndexAPIView(APIView):
    def _get_authors(self, author_id):
        if author_id == 'me':
            user = get_current_user()
            if user is None:
                return []

            username, domain = user.email.split('@', 1)
            email_query = '{}+%@{}'.format(username, domain)

            return list(Author.query.filter(
                or_(
                    Author.email.like(email_query),
                    Author.email == user.email,
                )
            ))
        try:
            author_id = UUID(author_id)
        except ValueError:
            return []

        author = Author.query.get(author_id)
        if author is None:
            return []
        return [author]

    def get(self, author_id):
        if author_id == 'me' and not get_current_user():
            return '', 401

        authors = self._get_authors(author_id)
        if not authors:
            return '', 404

        queryset = Build.query.options(
            joinedload('project'),
            joinedload('author'),
            joinedload('source').joinedload('revision'),
        ).filter(
            Build.author_id.in_([a.id for a in authors])
        ).order_by(Build.date_created.desc(), Build.date_started.desc())

        return self.paginate(queryset)

    def get_stream_channels(self, author_id):
        author = self._get_author(author_id)
        if not author:
            return []
        return ['authors:{0}:builds'.format(author.id.hex)]
