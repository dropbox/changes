from __future__ import absolute_import, division, unicode_literals

from changes.api.base import APIView
from changes.api.auth import get_current_user
from changes.models import Author

from changes.utils.phabricator_utils import PhabricatorRequest

import requests


class AuthorPhabricatorDiffsAPIView(APIView):
    """
    Hits phabricator to get a list of the user's diffs in review. This is
    the first (possibly only) api call that hits phabricator: we can't rely on
    local data because there's no way to know whether a diff has been abandoned
    or not.
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
            request = PhabricatorRequest()
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

            return diff_info
        except requests.exceptions.ConnectionError:
            return 'Unable to connect to Phabricator', 503
