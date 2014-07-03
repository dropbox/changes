from __future__ import absolute_import, division, unicode_literals

from flask.ext.restful import reqparse

from changes.api.auth import requires_auth
from changes.api.base import APIView
from changes.config import db
from changes.jobs.import_repo import import_repo
from changes.models import Repository, RepositoryBackend, RepositoryStatus

BACKEND_CHOICES = ('git', 'hg', 'unknown')

STATUS_CHOICES = ('active', 'inactive')


class RepositoryDetailsAPIView(APIView):
    parser = reqparse.RequestParser()
    parser.add_argument('url', type=unicode)
    parser.add_argument('backend', choices=BACKEND_CHOICES)
    parser.add_argument('status', choices=STATUS_CHOICES)

    def get(self, repository_id):
        repo = Repository.query.get(repository_id)
        if repo is None:
            return '', 404

        return self.respond(repo)

    @requires_auth
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
        db.session.commit()

        if needs_import:
            import_repo.delay_if_needed(
                repo_id=repo.id.hex,
                task_id=repo.id.hex,
            )

        return self.respond(repo)
