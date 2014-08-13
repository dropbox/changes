from __future__ import absolute_import, division, unicode_literals

from flask.ext.restful import reqparse

from changes.api.auth import requires_admin
from changes.api.base import APIView
from changes.config import db
from changes.db.utils import create_or_update
from changes.jobs.import_repo import import_repo
from changes.models import (
    ItemOption, Repository, RepositoryBackend, RepositoryStatus
)

BACKEND_CHOICES = ('git', 'hg', 'unknown')

STATUS_CHOICES = ('active', 'inactive')

OPTION_DEFAULTS = {
    'phabricator.callsign': '',
}


class RepositoryDetailsAPIView(APIView):
    parser = reqparse.RequestParser()
    parser.add_argument('url', type=unicode)
    parser.add_argument('backend', choices=BACKEND_CHOICES)
    parser.add_argument('status', choices=STATUS_CHOICES)
    for option in OPTION_DEFAULTS.keys():
        parser.add_argument(option)

    def _get_options(self, repo):
        options = dict(
            (o.name, o.value) for o in ItemOption.query.filter(
                ItemOption.item_id == repo.id,
            )
        )
        for key, value in OPTION_DEFAULTS.iteritems():
            options.setdefault(key, value)

        return options

    def get(self, repository_id):
        repo = Repository.query.get(repository_id)
        if repo is None:
            return '', 404

        context = self.serialize(repo)
        context['options'] = self._get_options(repo)

        return self.respond(context, serialize=False)

    @requires_admin
    def post(self, repository_id):
        repo = Repository.query.get(repository_id)
        if repo is None:
            return '', 404

        args = self.parser.parse_args()

        if args.url:
            repo.url = args.url
        if args.backend:
            repo.backend = RepositoryBackend[args.backend]

        needs_import = False
        if args.status == 'inactive':
            repo.status = RepositoryStatus.inactive
        elif args.status == 'active' and repo.status == RepositoryStatus.inactive:
            repo.status = RepositoryStatus.active
            needs_import = True

        db.session.add(repo)

        for name in OPTION_DEFAULTS.keys():
            value = args[name]
            if value is None:
                continue

            # special case phabricator.callsign since we can't enforce a unique
            # constraint
            if name == 'phabricator.callsign':
                existing = ItemOption.query.filter(
                    ItemOption.item_id != repo.id,
                    ItemOption.name == name,
                    ItemOption.value == value,
                ).first()
                if existing:
                    return '{"error": "A repository already exists with the given Phabricator callsign"}', 400

            create_or_update(ItemOption, where={
                'item_id': repo.id,
                'name': name,
            }, values={
                'value': value,
            })

        db.session.commit()

        if needs_import:
            import_repo.delay_if_needed(
                repo_id=repo.id.hex,
                task_id=repo.id.hex,
            )

        context = self.serialize(repo)
        context['options'] = self._get_options(repo)

        return self.respond(context, serialize=False)
