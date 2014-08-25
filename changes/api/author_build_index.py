from __future__ import absolute_import, division, unicode_literals

from sqlalchemy.orm import joinedload

from changes.api.base import APIView
from changes.api.auth import get_current_user
from changes.models import Author, Build


class AuthorBuildIndexAPIView(APIView):
    def get(self, author_id):
        authors = Author.find(author_id, get_current_user())
        if not authors and author_id == 'me':
            return '', 401
        elif not authors:
            return '', 404

        queryset = Build.query.options(
            joinedload('project'),
            joinedload('author'),
            joinedload('source').joinedload('revision'),
        ).filter(
            Build.author_id.in_([a.id for a in authors])
        ).order_by(Build.date_created.desc(), Build.date_started.desc())

        return self.paginate(queryset)
