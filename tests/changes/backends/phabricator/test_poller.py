from __future__ import absolute_import

import json
import httpretty
import mock
import os.path

from exam import fixture
from phabricator import Phabricator
from urlparse import parse_qs

from changes.config import db
from changes.models import Repository, Project
from changes.backends.phabricator.poller import PhabricatorPoller
from changes.testutils import BackendTestCase


class BaseTestCase(BackendTestCase):
    provider = 'phabricator'
    poller_cls = PhabricatorPoller
    client_options = {
        'host': 'http://phabricator.example.com/api/',
        'username': 'test',
        'certificate': 'the cert',
    }
    client_session_key = 'session key'
    client_connection_id = 'connection id'

    def setUp(self):
        self.repo = Repository(url='https://github.com/dropbox/changes.git')
        self.project = Project(repository=self.repo, name='test', slug='test')

        db.session.add(self.repo)
        db.session.add(self.project)

    def load_fixture(self, filename):
        filepath = os.path.join(
            os.path.dirname(__file__),
            filename,
        )
        with open(filepath, 'rb') as fp:
            return fp.read()

    def make_project_entity(self, project, remote_id):
        return self.make_entity('project', project.id, remote_id)

    def get_poller(self):
        return self.poller_cls(self.phabricator)

    def load_request_params(self, request):
        result = json.loads(parse_qs(request.body)['params'][0])
        del result['__conduit__']
        return result

    @fixture
    def phabricator(self):
        client = Phabricator(**self.client_options)
        client.conduit = {
            'sessionKey': self.client_session_key,
            'connectionID': self.client_connection_id,
        }
        return client


class PhabricatorPollerTest(BaseTestCase):
    @httpretty.activate
    @mock.patch.object(PhabricatorPoller, 'sync_revision')
    def test_sync_revision_list(self, sync_revision):
        httpretty.register_uri(
            httpretty.POST, 'http://phabricator.example.com/api/differential.query',
            body=self.load_fixture('fixtures/POST/differential.query.json'),
            streaming=True)

        self.make_project_entity(self.project, 'Server')

        poller = self.get_poller()
        poller.sync_revision_list()

        request = httpretty.last_request()
        assert self.load_request_params(request) == {
            'arcanistProjects': ['Server'],
            'limit': 100,
        }

        assert len(sync_revision.mock_calls) == 2

        _, args, kwargs = sync_revision.mock_calls[0]
        assert len(args) == 2
        assert not kwargs
        assert args[0] == self.project
        assert args[1]['id'] == '23788'

        _, args, kwargs = sync_revision.mock_calls[1]
        assert len(args) == 2
        assert not kwargs
        assert args[0] == self.project
        assert args[1]['id'] == '23766'

    @httpretty.activate
    @mock.patch.object(PhabricatorPoller, 'sync_diff_list')
    def test_sync_revision(self, sync_diff_list):
        httpretty.register_uri(
            httpretty.POST, 'http://phabricator.example.com/api/differential.getcommitmessage',
            body=self.load_fixture('fixtures/POST/differential.getcommitmessage.json'))

        revision = json.loads(
            self.load_fixture('fixtures/POST/differential.query.json')
        )['result'][0]
        message = json.loads(
            self.load_fixture('fixtures/POST/differential.getcommitmessage.json')
        )['result']

        poller = self.get_poller()

        change = poller.sync_revision(self.project, revision)

        request = httpretty.last_request()
        assert self.load_request_params(request) == {
            'revision_id': '23788',
        }

        assert change.label == 'D23788: Adding new settings tabs'
        assert change.message == message

        sync_diff_list.assert_called_once_with(change, revision['id'])

    @httpretty.activate
    @mock.patch.object(PhabricatorPoller, 'sync_diff')
    def test_sync_diff_list(self, sync_diff):
        httpretty.register_uri(
            httpretty.POST, 'http://phabricator.example.com/api/differential.querydiffs',
            body=self.load_fixture('fixtures/POST/differential.querydiffs.json'))

        change = self.create_change(self.project)

        poller = self.get_poller()
        poller.sync_diff_list(change, '23788')

        request = httpretty.last_request()
        assert self.load_request_params(request) == {
            'revisionIDs': ['23788'],
        }

        assert len(sync_diff.mock_calls) == 2

        _, args, kwargs = sync_diff.mock_calls[0]
        assert len(args) == 2
        assert not kwargs
        assert args[0] == change
        assert args[1]['id'] == '16161'

        _, args, kwargs = sync_diff.mock_calls[1]
        assert len(args) == 2
        assert not kwargs
        assert args[0] == change
        assert args[1]['id'] == '16163'

    @httpretty.activate
    def test_sync_diff(self):
        diff = json.loads(
            self.load_fixture('fixtures/POST/differential.querydiffs.json')
        )['result']['16161']

        change = self.create_change(self.project)

        poller = self.get_poller()
        patch = poller.sync_diff(change, diff)

        assert patch.label == 'Diff ID 16161: Initial'
        assert patch.change == change
        assert patch.parent_revision_sha == 'ca7a7927948babe35652a9ea58f94e470ae9e51f'
