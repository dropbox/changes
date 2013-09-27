import uuid
import json

from flask import current_app as app
from unittest2 import TestCase

from changes.config import db
from changes.models import (
    Repository, Build, Project, Revision, RemoteEntity
)


class BackendTestCase(TestCase):
    backend_cls = None
    backend_options = {}
    provider = None

    def get_backend(self):
        return self.backend_cls(
            app=app, **self.backend_options
        )

    def make_entity(self, type, internal_id, remote_id):
        entity = RemoteEntity(
            type=type,
            remote_id=remote_id,
            internal_id=internal_id,
            provider=self.provider,
        )
        db.session.add(entity)
        return entity


class APITestCase(TestCase):
    def setUp(self):
        self.client = app.test_client()

        self.repo = Repository(url='https://github.com/dropbox/changes.git')
        db.session.add(self.repo)

        self.project = Project(repository=self.repo, name='test', slug='test')
        db.session.add(self.project)

        self.project2 = Project(repository=self.repo, name='test2', slug='test2')
        db.session.add(self.project2)

    def create_build(self, project, **kwargs):
        revision = Revision(
            sha=uuid.uuid4().hex,
            repository=project.repository
        )
        db.session.add(revision)

        kwargs.setdefault('label', 'Sample')

        build = Build(
            repository=project.repository,
            project=project,
            parent_revision=revision,
            parent_revision_sha=revision.sha,
            **kwargs
        )
        db.session.add(build)

        return build

    def unserialize(self, response):
        assert response.headers['Content-Type'] == 'application/json'
        return json.loads(response.data)
