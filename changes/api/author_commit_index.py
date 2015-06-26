from __future__ import absolute_import, division, unicode_literals

from sqlalchemy.orm import joinedload

from collections import OrderedDict, defaultdict

from changes.api.base import APIView
from changes.api.auth import get_current_user
from changes.models import Author, Build, Source, Revision


class AuthorCommitIndexAPIView(APIView):

    """
    Gets a list of commits by an author, and their associated builds

    Return format is a serialized list of sources, each with a builds
    attribute containing a list of builds (this differs from project_commit_index,
    which uses revisions instead of sources.)

    Note that builds may come from different projects.
    """

    def get(self, author_id):
        authors = Author.find(author_id, get_current_user())
        if not authors and author_id == 'me':
            return '', 401
        elif not authors:
            return '', 404

        # grab every build for every commit (by one author). We'll group
        # them together: returning a list of revisions each with a builds
        # attribute
        # TODO: I assume this will become inefficient at some point.

        # serialize everything now so that we batch any needed data fetching
        # we'll still rearrange things later
        commit_builds_list = self.serialize(list(Build.query.join(
            Source, Build.source_id == Source.id,
        ).join(
            Revision, Source.revision_sha == Revision.sha
        ).options(
            joinedload('project'),
            joinedload('author'),
            joinedload('source').joinedload('revision'),
        ).filter(
            Revision.author_id.in_([a.id for a in authors]),
            Source.patch_id.is_(None),
        ).order_by(
            Revision.date_created.desc(),
            Build.date_created.desc(),
            Build.date_started.desc()
        )))

        # rearrange to a list of sources, each with a builds attribute
        builds_map = defaultdict(list)
        revision_list = OrderedDict()

        for build in commit_builds_list:
            sha = build['source']['revision']['sha']
            source = build['source']
            del build['source']

            builds_map[sha].append(build)
            if sha not in revision_list:
                revision_list[sha] = source

        for (sha, revision) in revision_list.items():
            revision['builds'] = builds_map[sha]

        return self.respond(revision_list.values(), serialize=False)
