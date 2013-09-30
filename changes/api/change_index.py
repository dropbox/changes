from __future__ import absolute_import, division, unicode_literals

from sqlalchemy.orm import joinedload

from changes.api.base import APIView
from changes.models import Change, Build


class ChangeIndexAPIView(APIView):
    def get(self):
        change_list = list(
            Change.query.options(
                joinedload(Change.project),
                joinedload(Change.author),
            ).order_by(Change.date_created.desc())
        )[:100]

        # TODO(dcramer): denormalize this
        for change in change_list:
            try:
                change.latest_build = Build.query.filter_by(
                    change=change,
                ).order_by(
                    Build.date_created.desc(),
                    Build.date_started.desc()
                )[0]
            except IndexError:
                change.latestBuild = None

        context = {
            'changes': change_list,
        }

        return self.respond(context)
