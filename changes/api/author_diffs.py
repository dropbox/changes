from __future__ import absolute_import, division, unicode_literals

from changes.api.base import APIView
from changes.api.auth import get_current_user
from changes.config import db
from changes.models import Author, Build, PhabricatorDiff

from collections import defaultdict

from changes.utils.phabricator_utils import PhabricatorClient

import requests


class AuthorPhabricatorDiffsAPIView(APIView):
    """
    Hits phabricator to get a list of the user's diffs in review. This is the
    first (possibly only) changes api call that hits phabricator: we can't rely
    on local data because there's no way to know whether a diff has been
    abandoned or not.
    """

    def get(self, author_id):
        authors = Author.find(author_id, get_current_user())
        if not authors and author_id == 'me':
            return '''Either there is no current user or you are not in the
              author table''', 401
        elif not authors:
            return 'author not found', 404

        try:
            author_email = authors[0].email
            request = PhabricatorClient()
            request.connect()
            user_info = request.call('user.query', {'emails': [author_email]})

            if not user_info:
                return 'phabricator: %s not found' % author_email, 404

            author_phid = user_info[0]["phid"]

            diff_info = request.call('differential.query', {
                'authors': [author_phid],
                'status': "status-open"
            })

            diff_info.sort(key=lambda k: -1 * int(k['dateModified']))

        except requests.exceptions.ConnectionError:
            return 'Unable to connect to Phabricator', 503

        if not diff_info:
            # No diffs, no point in trying to find builds.
            return self.respond([])

        rows = list(db.session.query(
            PhabricatorDiff, Build
        ).join(
            Build, Build.source_id == PhabricatorDiff.source_id
        ).filter(
            PhabricatorDiff.revision_id.in_([d['id'] for d in diff_info])
        ))

        serialized_builds = zip(
            self.serialize([row.Build for row in rows]),
            [row.PhabricatorDiff for row in rows]
        )

        builds_map = defaultdict(list)
        for build, phabricator_diff in serialized_builds:
            builds_map[str(phabricator_diff.revision_id)].append(build)

        for d in diff_info:
            d['builds'] = builds_map[str(d['id'])]

        return self.respond(diff_info)
