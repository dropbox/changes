from __future__ import absolute_import, division, unicode_literals

from cStringIO import StringIO
from flask import current_app as app, request
from sqlalchemy.orm import joinedload

from changes.api.base import APIView, param
from changes.config import db
from changes.db.utils import create_or_update
from changes.models import (
    Build, Author, Project, Repository, Patch
)


class AuthorValidator(object):
    def __call__(self, value):
        parsed = self.parse(value)
        if not parsed:
            raise ValueError(value)
        return Author.query.filter_by(email=parsed.email)[0]

    def parse(label):
        import re
        match = re.match(r'^(.+) <([^>]+)>$', label)
        if not match:
            return
        return match.group(1), match.group(2)


class BuildIndexAPIView(APIView):
    def get_backend(self, app=app):
        # TODO this should be automatic via a project
        from changes.backends.koality.backend import KoalityBackend
        return KoalityBackend(
            app=app,
            base_url=app.config['KOALITY_URL'],
            api_key=app.config['KOALITY_API_KEY'],
        )

    def get(self):
        build_list = list(
            Build.query.options(
                joinedload(Build.project),
                joinedload(Build.author),
            ).order_by(Build.date_created.desc())
        )[:100]

        context = {
            'builds': build_list,
        }

        return self.respond(context)

    @param('project', lambda x: Project.query.filter_by(slug=x)[0])
    @param('sha')
    @param('author', AuthorValidator, required=False)
    def post(self, project, sha, author=None, patch_label=None,
             patch_url=None, patch=None):

        patch_file = request.files.get('patch')
        patch_label = request.form.get('patch_label')
        patch_url = request.form.get('patch_url')

        if patch_file and not patch_label:
            raise ValueError('patch_label')

        repository = Repository.query.get(project.repository_id)

        # if author:
        #     author = create_or_update(Author, where={
        #         'email': author[1],
        #     }, values={
        #         'name': author[0],
        #     })

        if patch_file:
            fp = StringIO()
            for line in patch_file:
                fp.write(line)

            patch = Patch(
                repository=repository,
                project=project,
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
            project=project,
            repository=repository,
            # author=author,
            label=label,
            parent_revision_sha=sha,
            patch=patch,
        )
        db.session.add(build)

        backend = self.get_backend()
        backend.create_build(build)

        context = {
            'build': {
                'id': build.id.hex,
            },
        }

        return self.respond(context)
