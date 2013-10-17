from __future__ import absolute_import

import httpretty
import os.path

from flask import current_app
from uuid import UUID

from changes.config import db
from changes.constants import Status, Result
from changes.models import Repository, Project, RemoteEntity
from changes.backends.jenkins.builder import JenkinsBuilder
from changes.testutils import BackendTestCase


class BaseTestCase(BackendTestCase):
    provider = 'jenkins'
    builder_cls = JenkinsBuilder
    builder_options = {
        'base_url': 'http://jenkins.example.com',
    }

    def setUp(self):
        self.repo = Repository(url='https://github.com/dropbox/changes.git')
        self.project = Project(repository=self.repo, name='test', slug='test')
        self.project_entity = RemoteEntity(
            provider=self.provider,
            internal_id=self.project.id,
            remote_id='server',
            type='job',
        )

        db.session.add(self.repo)
        db.session.add(self.project)
        db.session.add(self.project_entity)

    def get_builder(self):
        return self.builder_cls(app=current_app, **self.builder_options)

    def load_fixture(self, filename):
        filepath = os.path.join(
            os.path.dirname(__file__),
            filename,
        )
        with open(filepath, 'rb') as fp:
            return fp.read()


class CreateBuildTest(BaseTestCase):
    @httpretty.activate
    def test_queued_creation(self):
        httpretty.register_uri(
            httpretty.POST, 'http://jenkins.example.com/job/server/build/api/json/',
            body='',
            status=201)

        httpretty.register_uri(
            httpretty.GET, 'http://jenkins.example.com/queue/api/json/',
            body=self.load_fixture('fixtures/GET/queue_list.json'))

        httpretty.register_uri(
            httpretty.GET, 'http://jenkins.example.com/job/server/api/json/',
            body=self.load_fixture('fixtures/GET/job_list.json'))

        build = self.create_build(
            self.project,
            id=UUID('81d1596fd4d642f4a6bdf86c45e014e8'))

        builder = self.get_builder()
        builder.create_build(build)

        entity = RemoteEntity.query.filter_by(
            provider=self.provider,
            internal_id=build.id,
            type='build',
        )[0]

        assert entity.remote_id == 'queue:13'
        assert entity.data == {
            'build_no': None,
            'item_id': 13,
            'job_name': 'server',
            'queued': True,
        }

    @httpretty.activate
    def test_active_creation(self):
        httpretty.register_uri(
            httpretty.POST, 'http://jenkins.example.com/job/server/build/api/json/',
            body='',
            status=201)

        httpretty.register_uri(
            httpretty.GET, 'http://jenkins.example.com/queue/api/json/',
            body=self.load_fixture('fixtures/GET/queue_list.json'))

        httpretty.register_uri(
            httpretty.GET, 'http://jenkins.example.com/job/server/api/json/',
            body=self.load_fixture('fixtures/GET/job_list.json'))

        build = self.create_build(
            self.project,
            id=UUID('f9481a17aac446718d7893b6e1c6288b'))

        builder = self.get_builder()
        builder.create_build(build)

        entity = RemoteEntity.query.filter_by(
            provider=self.provider,
            internal_id=build.id,
            type='build',
        )[0]

        assert entity.remote_id == 'server#1'
        assert entity.data == {
            'build_no': 1,
            'item_id': None,
            'job_name': 'server',
            'queued': False,
        }


class SyncBuildTest(BaseTestCase):
    @httpretty.activate
    def test_waiting_in_queue(self):
        httpretty.register_uri(
            httpretty.GET, 'http://jenkins.example.com/queue/item/13/api/json/',
            body=self.load_fixture('fixtures/GET/queue_details_pending.json'))

        build = self.create_build(
            self.project,
            id=UUID('81d1596fd4d642f4a6bdf86c45e014e8'))

        entity = RemoteEntity(
            provider=self.provider,
            internal_id=build.id,
            remote_id='queue:13',
            type='build',
            data={
                'build_no': None,
                'item_id': 13,
                'job_name': 'server',
                'queued': True,
            },
        )
        db.session.add(entity)

        builder = self.get_builder()
        builder.sync_build(build)

        assert build.status == Status.queued

    @httpretty.activate
    def test_cancelled_in_queue(self):
        httpretty.register_uri(
            httpretty.GET, 'http://jenkins.example.com/queue/item/13/api/json/',
            body=self.load_fixture('fixtures/GET/queue_details_cancelled.json'))

        build = self.create_build(
            self.project,
            id=UUID('81d1596fd4d642f4a6bdf86c45e014e8'))

        entity = RemoteEntity(
            provider=self.provider,
            internal_id=build.id,
            remote_id='queue:13',
            type='build',
            data={
                'build_no': None,
                'item_id': 13,
                'job_name': 'server',
                'queued': True,
            },
        )
        db.session.add(entity)

        builder = self.get_builder()
        builder.sync_build(build)

        assert build.status == Status.finished
        assert build.result == Result.aborted

    @httpretty.activate
    def test_queued_to_active(self):
        httpretty.register_uri(
            httpretty.GET, 'http://jenkins.example.com/queue/item/13/api/json/',
            body=self.load_fixture('fixtures/GET/queue_details_building.json'))
        httpretty.register_uri(
            httpretty.GET, 'http://jenkins.example.com/job/server/2/api/json/',
            body=self.load_fixture('fixtures/GET/job_details_building.json'))

        build = self.create_build(
            self.project,
            id=UUID('81d1596fd4d642f4a6bdf86c45e014e8'))

        entity = RemoteEntity(
            provider=self.provider,
            internal_id=build.id,
            remote_id='queue:13',
            type='build',
            data={
                'build_no': None,
                'item_id': 13,
                'job_name': 'server',
                'queued': True,
            },
        )
        db.session.add(entity)

        builder = self.get_builder()
        builder.sync_build(build)

        entity = RemoteEntity.query.get(entity.id)

        assert entity.data['build_no'] == 2
        assert build.status == Status.in_progress
        assert build.date_started is not None

    @httpretty.activate
    def test_success_result(self):
        httpretty.register_uri(
            httpretty.GET, 'http://jenkins.example.com/job/server/2/api/json/',
            body=self.load_fixture('fixtures/GET/job_details_success.json'))

        build = self.create_build(
            self.project,
            id=UUID('81d1596fd4d642f4a6bdf86c45e014e8'))

        entity = RemoteEntity(
            provider=self.provider,
            internal_id=build.id,
            remote_id='server#2',
            type='build',
            data={
                'build_no': 2,
                'item_id': 13,
                'job_name': 'server',
                'queued': False,
            },
        )
        db.session.add(entity)

        builder = self.get_builder()
        builder.sync_build(build)

        entity = RemoteEntity.query.get(entity.id)

        assert entity.data['build_no'] == 2
        assert build.status == Status.finished
        assert build.result == Result.passed
        assert build.duration == 8875000
        assert build.date_finished is not None

    @httpretty.activate
    def test_failed_result(self):
        httpretty.register_uri(
            httpretty.GET, 'http://jenkins.example.com/job/server/2/api/json/',
            body=self.load_fixture('fixtures/GET/job_details_failed.json'))

        build = self.create_build(
            self.project,
            id=UUID('81d1596fd4d642f4a6bdf86c45e014e8'))

        entity = RemoteEntity(
            provider=self.provider,
            internal_id=build.id,
            remote_id='server#2',
            type='build',
            data={
                'build_no': 2,
                'item_id': 13,
                'job_name': 'server',
                'queued': False,
            },
        )
        db.session.add(entity)

        builder = self.get_builder()
        builder.sync_build(build)

        entity = RemoteEntity.query.get(entity.id)

        assert entity.data['build_no'] == 2
        assert build.status == Status.finished
        assert build.result == Result.failed
        assert build.duration == 8875000
        assert build.date_finished is not None
