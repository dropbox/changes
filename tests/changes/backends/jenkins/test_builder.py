from __future__ import absolute_import

import httpretty
import os.path

from flask import current_app
from uuid import UUID

from changes.config import db
from changes.constants import Status, Result
from changes.models import Repository, Project, RemoteEntity, TestCase, Patch
from changes.backends.jenkins.builder import JenkinsBuilder
from changes.testutils import BackendTestCase


SAMPLE_DIFF = """diff --git a/README.rst b/README.rst
index 2ef2938..ed80350 100644
--- a/README.rst
+++ b/README.rst
@@ -1,5 +1,5 @@
 Setup
------
+====="""


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


# TODO(dcramer): these tests need to ensure we're passing the right parameters
# to jenkins
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

        assert entity.remote_id
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

        assert entity.remote_id
        assert entity.data == {
            'build_no': 1,
            'item_id': None,
            'job_name': 'server',
            'queued': False,
        }

    @httpretty.activate
    def test_patch(self):
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

        patch = Patch(
            repository=self.repo,
            project=self.project,
            parent_revision_sha='7ebd1f2d750064652ef5bbff72452cc19e1731e0',
            label='D1345',
            diff=SAMPLE_DIFF,
        )
        db.session.add(patch)

        build = self.create_build(
            self.project,
            patch=patch,
            revision_sha=patch.parent_revision_sha,
            id=UUID('81d1596fd4d642f4a6bdf86c45e014e8')
        )

        builder = self.get_builder()
        builder.create_build(build)


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
        assert build.duration == 8875
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
        assert build.duration == 8875
        assert build.date_finished is not None

    @httpretty.activate
    def test_does_sync_test_report(self):
        httpretty.register_uri(
            httpretty.GET, 'http://jenkins.example.com/job/server/2/api/json/',
            body=self.load_fixture('fixtures/GET/job_details_with_test_report.json'))

        httpretty.register_uri(
            httpretty.GET, 'http://jenkins.example.com/job/server/2/testReport/api/json/',
            body=self.load_fixture('fixtures/GET/job_test_report.json'))

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

        test_list = sorted(TestCase.query.filter_by(build=build), key=lambda x: x.duration)

        assert len(test_list) == 2
        assert test_list[0].name == 'Test'
        assert test_list[0].package == 'tests.changes.handlers.test_xunit'
        assert test_list[0].result == Result.skipped
        assert test_list[0].message == 'collection skipped'
        assert test_list[0].duration == 0

        assert test_list[1].name == 'test_simple'
        assert test_list[1].package == 'tests.changes.api.test_build_details.BuildDetailsTest'
        assert test_list[1].result == Result.passed
        assert test_list[1].message == ''
        assert test_list[1].duration == 155
