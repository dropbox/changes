from __future__ import absolute_import, division, unicode_literals

from flask import session
from sqlalchemy.orm import joinedload

from changes.api.base import APIView
from changes.models import Author, Build


class AuthorBuildIndexAPIView(APIView):
    def _get_author(self, author_id):
        if author_id == 'me':
            if not session.get('email'):
                return
            return Author.query.filter_by(email=session['email']).first()
        return Author.query.get(author_id)

    def get(self, author_id):
        author = self._get_author(author_id)
        if not author:
            return self.respond([])

        queryset = Build.query.options(
            joinedload('project', innerjoin=True),
            joinedload('author'),
        ).filter(
            Build.author_id == author.id,
        ).order_by(Build.date_created.desc(), Build.date_started.desc())

        return self.paginate(queryset)

    def get_stream_channels(self, author_id):
        author = self._get_author(author_id)
        if not author:
            return []
        return ['authors:{0}:builds'.format(author.id.hex)]
