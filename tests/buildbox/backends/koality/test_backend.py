from __future__ import absolute_import

import json
import mock
import os

from buildbox.backends.koality.backend import KoalityBackend
from buildbox.models import (
    Repository, Revision, Project, Build, EntityType
)
from buildbox.testutils import BackendTestCase


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
        return url[len(self.base_url) + 1:].strip('/').replace('/', '__') + '.json'


class KoalityBackendTestCase(BackendTestCase):
    backend_cls = KoalityBackend
    backend_options = {
        'base_url': 'https://koality.example.com',
        'api_key': 'a' * 12,
    }
    provider = 'koality'

    def setUp(self):
        self.patcher = mock.patch.object(
            KoalityBackend,
            '_get_response',
            MockedResponse(self.backend_options['base_url']),
        )
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

        backend = self.get_backend()

        with backend.get_session() as session:
            self.repo = Repository(url='https://github.com/dropbox/buildbox.git')
            self.project = Project(repository=self.repo, name='test', slug='test')
            session.add(self.repo)
            session.add(self.project)


class ListBuildsTest(KoalityBackendTestCase):
    def test_simple(self):
        backend = self.get_backend()

        self.make_entity(EntityType.project, self.project.id, 1)

        results = backend.list_builds(self.project)
        assert len(results) == 2


class SyncBuildDetailsTest(KoalityBackendTestCase):
    def test_simple(self):
        backend = self.get_backend()

        with backend.get_session() as session:
            revision = Revision(sha='a' * 40, repository=self.repo)
            build = Build(
                repository=self.repo, project=self.project, label='test',
                parent_revision=revision,
            )
            session.add(revision)
            session.add(build)

        self.make_entity(EntityType.project, self.project.id, 1)
        self.make_entity(EntityType.build, build.id, 1)

        backend.sync_build_details(build)
