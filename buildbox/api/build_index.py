from cStringIO import StringIO
from flask import current_app as app, request
from sqlalchemy.orm import joinedload

from buildbox.api.base import APIView
from buildbox.config import db
from buildbox.db.utils import create_or_update
from buildbox.models import (
    Build, Revision, Author, Project, Repository, Patch
)


def parse_author(label):
    import re
    match = re.match(r'^(.+) <([^>]+)>$', label)
    if not match:
        return
    return match.group(1), match.group(2)


class BuildIndexAPIView(APIView):
    def get(self):
        build_list = list(
            Build.query.options(
                joinedload(Build.project),
                joinedload(Build.author),
                joinedload(Build.parent_revision),
                joinedload(Build.parent_revision, Revision.author),
            ).order_by(Build.date_created.desc())
        )[:100]

        context = {
            'builds': build_list,
        }

        return self.respond(context)

    def post(self):
        project = request.form['project']
        revision = request.form['revision']
        author = request.form['author']

        patch_file = request.files.get('patch')
        patch_label = request.form.get('patch_label')
        patch_url = request.form.get('patch_url')

        if patch_file and not patch_label:
            raise ValueError('patch_label')

        author = parse_author(request.form['author'])
        if not author:
            raise ValueError('author')

        project = Project.query.join(Repository).get(project)

        revision = create_or_update(Revision, where={
            'sha': revision,
            'repository': project.reopsitory
        })

        author = create_or_update(Author, where={
            'email': author[1],
        }, values={
            'name': author[0],
        })

        if patch_file:
            fp = StringIO()
            for line in patch_file:
                fp.write(line)

            patch = Patch(
                repository=project.repository,
                project=project,
                parent_revision=revision,
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
            label = revision

        build = Build(
            project=project,
            repository=project.repository,
            author=author,
            label=label,
            parent_revision_sha=revision,
            patch=patch,
        )
        db.session.add(build)

        # TODO this should be automatic via a project
        from buildbox.backends.koality.backend import KoalityBackend
        backend = KoalityBackend(
            app=app,
            base_url=app.config['KOALITY_URL'],
            api_key=app.config['KOALITY_API_KEY'],
        )

        backend.create_build(build)
        db.commit()

        context = {
            'build': {
                'id': build.id,
            },
        }

        return self.respond(context)
