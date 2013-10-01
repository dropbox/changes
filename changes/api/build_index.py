from __future__ import absolute_import, division, unicode_literals

from cStringIO import StringIO
from flask import current_app as app, request
from sqlalchemy.orm import joinedload

from changes.api.base import APIView, param
from changes.api.validators.author import AuthorValidator
from changes.config import db, pubsub
from changes.models import Build, Repository, Patch, Change


class BuildIndexAPIView(APIView):
    def get_backend(self, app=app):
        # TODO this should be automatic via a project
        from changes.backends.koality.backend import KoalityBackend
        return KoalityBackend(
            app=app,
            base_url=app.config['KOALITY_URL'],
            api_key=app.config['KOALITY_API_KEY'],
        )

    @param('change_id', lambda x: Change.query.get(x), dest='change')
    def get(self, change):
        build_list = list(
            Build.query.options(
                joinedload(Build.project),
                joinedload(Build.author),
            ).filter_by(
                change=change,
            ).order_by(Build.date_created.desc(), Build.date_started.desc())
        )[:100]

        context = {
            'builds': build_list,
        }

        return self.respond(context)

    @param('change_id', lambda x: Change.query.get(x), dest='change')
    @param('sha')
    @param('author', AuthorValidator(), required=False)
    @param('patch[label]', required=False, dest='patch_label')
    @param('patch[url]', required=False, dest='patch_url')
    def post(self, change, sha, author=None, patch_label=None,
             patch_url=None, patch=None):

        if request.form.get('patch'):
            raise ValueError('patch')

        patch_file = request.files.get('patch')
        patch_label = request.form.get('patch_label')
        patch_url = request.form.get('patch_url')

        if patch_file and not patch_label:
            raise ValueError('patch_label')

        repository = Repository.query.get(change.repository_id)

        if patch_file:
            fp = StringIO()
            for line in patch_file:
                fp.write(line)

            patch = Patch(
                repository=repository,
                project=change.project,
                parent_revision_sha=sha,
                label=patch_label,
                url=patch_url,
                diff=fp.getvalue(),
            )
            db.session.add(patch)
        else:
            patch = None

        if patch_label:
            label = patch_label
        else:
            label = sha[:12]

        build = Build(
            project=change.project,
            repository=repository,
            author=author,
            label=label,
            parent_revision_sha=sha,
            patch=patch,
        )
        db.session.add(build)

        backend = self.get_backend()
        backend.create_build(build)

        pubsub.publish('builds', {
            'data': self.as_json(build),
            'event': 'build.update',
        })

        context = {
            'build': {
                'id': build.id.hex,
            },
        }

        return self.respond(context)
