from __future__ import absolute_import, division, unicode_literals

from sqlalchemy.orm import joinedload

from changes.api.base import APIView, error
from changes.api.auth import get_current_user
from changes.models.author import Author
from changes.models.build import Build


class AuthorBuildIndexAPIView(APIView):
    def get(self, author_id):
        if author_id == 'me' and not get_current_user():
            return error('Must be logged in to ask about yourself', http_code=401)
        authors = Author.find(author_id, get_current_user())
        if not authors:
            return self.respond([])

        queryset = Build.query.options(
            joinedload('project'),
            joinedload('author'),
            joinedload('source').joinedload('revision'),
        ).filter(
            Build.author_id.in_([a.id for a in authors])
        ).order_by(Build.date_created.desc(), Build.date_started.desc())

        return self.paginate(queryset)
