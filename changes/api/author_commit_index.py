from __future__ import absolute_import, division, unicode_literals

from flask_restful.reqparse import RequestParser

from sqlalchemy.orm import joinedload

from collections import defaultdict

from changes.api.base import APIView
from changes.api.auth import get_current_user
from changes.models.author import Author
from changes.models.build import Build
from changes.models.revision import Revision
from changes.models.source import Source


class AuthorCommitIndexAPIView(APIView):
    """
    Gets a list of commits by an author, and their associated builds

    Return format is a serialized list of sources, each with a builds
    attribute containing a list of builds (this differs from project_commit_index,
    which uses revisions instead of sources.)

    Note that builds may come from different projects.
    """

    get_parser = RequestParser()
    get_parser.add_argument('num_revs', type=int, location='args', default=10)

    def get(self, author_id):
        authors = Author.find(author_id, get_current_user())
        if not authors and author_id == 'me':
            return '', 401
        elif not authors:
            return '', 404

        args = self.get_parser.parse_args()

        # serialize everything when fetching so that we batch any needed data
        # fetching. we'll still rearrange things later

        # grab recent revisions by author (for any repository/project, which
        # means we can't use vcs commands)
        sources = self.serialize(list(Source.query.join(
            Revision, Source.revision_sha == Revision.sha
        ).filter(
            Revision.author_id.in_([a.id for a in authors]),
            Source.patch_id.is_(None),
        ).order_by(
            Revision.date_committed.desc(),
        ).limit(args.num_revs)))

        if not sources:
            return self.respond(sources)

        # grab builds for those revisions
        commit_builds_list = self.serialize(list(Build.query.options(
            joinedload('project'),
            joinedload('author'),
        ).filter(
            Build.source_id.in_([s['id'] for s in sources]),
        ).order_by(
            Build.date_created.desc(),
            Build.date_started.desc()
        )))

        # move builds into sources
        builds_map = defaultdict(list)

        for build in commit_builds_list:
            builds_map[build['source']['id']].append(build)

        for source in sources:
            source['builds'] = builds_map[source['id']]

        return self.respond(sources, serialize=False)
