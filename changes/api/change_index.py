from __future__ import absolute_import, division, unicode_literals

from sqlalchemy.orm import joinedload

from changes.api.base import APIView, param
from changes.api.validators.author import AuthorValidator
from changes.config import db
from changes.models import Change, Build, Project, Repository


class ChangeIndexAPIView(APIView):
    def get(self):
        change_list = list(
            Change.query.options(
                joinedload(Change.project),
                joinedload(Change.author),
            ).order_by(Change.date_modified.desc())
        )[:100]

        # TODO(dcramer): denormalize this
        for change in change_list:
            try:
                change.last_build = Build.query.filter_by(
                    change=change,
                ).order_by(
                    Build.date_created.desc(),
                    Build.date_started.desc()
                )[0]
            except IndexError:
                change.last_build = None

        context = {
            'changes': change_list,
        }

        return self.respond(context)

    @param('project', lambda x: Project.query.filter_by(slug=x)[0])
    @param('label')
    @param('key', required=False)
    @param('author', AuthorValidator(), required=False)
    @param('message', required=False)
    @param('date_created', required=False)
    @param('date_modified', required=False)
    def post(self, project, label, key=None, author=None, message=None,
             date_created=None, date_modified=None):
        repository = Repository.query.get(project.repository_id)

        change = Change(
            project=project,
            repository=repository,
            author=author,
            label=label,
        )
        db.session.add(change)

        context = {
            'change': {
                'id': change.id.hex,
            },
        }

        return self.respond(context)

    def get_stream_channels(self):
        return ['changes:*']
