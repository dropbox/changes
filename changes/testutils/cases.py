from __future__ import absolute_import

import mock
import uuid
import json
import unittest2

from exam import fixture
from flask import current_app as app

from changes.config import db
from changes.models import (
    Repository, Build, Project, Revision, RemoteEntity, Change
)


class TestCase(unittest2.TestCase):
    def setUp(self):
        self.repo = Repository(url='https://github.com/dropbox/changes.git')
        db.session.add(self.repo)

        self.project = Project(repository=self.repo, name='test', slug='test')
        db.session.add(self.project)

        self.project2 = Project(repository=self.repo, name='test2', slug='test2')
        db.session.add(self.project2)

        super(TestCase, self).setUp()

    @fixture
    def client(self):
        return app.test_client()

    def create_change(self, project, **kwargs):
        kwargs.setdefault('label', 'Sample')

        change = Change(
            hash=uuid.uuid4().hex,
            repository=project.repository,
            project=project,
            **kwargs
        )
        db.session.add(change)

        return change

    def create_build(self, project, **kwargs):
        revision = Revision(
            sha=uuid.uuid4().hex,
            repository=project.repository
        )
        db.session.add(revision)

        if not kwargs.get('change'):
            kwargs['change'] = self.create_change(project)

        kwargs.setdefault('label', 'Sample')

        build = Build(
            repository=project.repository,
            project=project,
            parent_revision_sha=revision.sha,
            **kwargs
        )
        db.session.add(build)

        return build

    def unserialize(self, response):
        assert response.headers['Content-Type'] == 'application/json'
        return json.loads(response.data)


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
        from changes.backends.base import BaseBackend

        super(APITestCase, self).setUp()

        self.mock_backend = mock.Mock(
            spec=BaseBackend(app=app),
        )
        self.patcher = mock.patch(
            'changes.api.base.APIView.get_backend',
            mock.Mock(return_value=self.mock_backend))
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
