from __future__ import absolute_import

import json
import mock
import os

from unittest2 import TestCase

from buildbox.backends.koality.backend import KoalityBackend
from buildbox.models import (
    Repository, Project, RemoteEntity, EntityType
)


class MockedResponse(object):
    fixture_root = os.path.join(os.path.dirname(__file__), 'fixtures')

    # used to mock out KoalityBackend._get_response
    def __init__(self, base_url):
        self.base_url = base_url

    def __call__(self, method, url, **kwargs):
        fixture = self.load_fixture(method, url, **kwargs)
        if fixture is None:
            # TODO:
            raise Exception

        fixture = os.path.join(self.fixture_root, fixture)

        with open(fixture) as fp:
            return json.load(fp)

    def load_fixture(self, method, url, **kwargs):
        if method == 'GET':
            return self.url_to_filename(url)

    def url_to_filename(self, url):
        assert url.startswith(self.base_url)
        return url[len(self.base_url) + 1:].replace('/', '__') + '.json'


class BackendTestCase(TestCase):
    backend_cls = None
    backend_options = {}
    provider = None

    def get_backend(self):
        return self.backend_cls(**self.backend_options)

    def make_entity(self, type, remote_id, internal_id):
        entity = RemoteEntity(
            type=type,
            remote_id=remote_id,
            internal_id=internal_id,
            provider=self.provider,
        )
        with self.get_backend().get_session() as session:
            session.add(entity)
        return entity


class ListBuildsTest(BackendTestCase):
    backend_cls = KoalityBackend
    backend_options = {
        'base_url': 'https://koality.example.com',
        'api_key': 'a' * 12,
    }

    def setUp(self):
        self.patcher = mock.patch.object(
            KoalityBackend,
            '_get_response',
            MockedResponse(self.backend_options['base_url']),
        )
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def test_simple(self):
        backend = self.get_backend()
        with backend.get_session() as session:
            repo = Repository(url='https://github.com/dropbox/buildbox.git')
            project = Project(repository=repo, name='test')
            session.add(repo)
            session.add(project)
        entity = self.make_entity(EntityType.project, 1, project.id)

        results = backend.list_builds(project, entity)
        assert len(results) == 2
