from __future__ import absolute_import, division, unicode_literals

from flask import request

from changes.api.base import APIView, error
from changes.config import db
from changes.models import Build, PhabricatorDiff


class PhabricatorInlineInfoAPIView(APIView):
    """
    The endpoint hit by phabricator to show inline info about what changes
    builds we've run for a diff.
    """

    def get(self):
        revision_id = request.args.get('revision_id')
        diff_id = request.args.get('diff_id')

        if not revision_id or not diff_id:
            return error('missing revision or diff id')

        # grab builds
        rows = list(db.session.query(
            Build, PhabricatorDiff
        ).join(
            PhabricatorDiff, Build.source_id == PhabricatorDiff.source_id,
        ).filter(
            PhabricatorDiff.revision_id == revision_id,
            PhabricatorDiff.diff_id == diff_id,
        ))

        return self.respond([row.Build for row in rows])
