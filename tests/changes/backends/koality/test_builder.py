from __future__ import absolute_import

import os
import responses

from datetime import datetime
from flask import current_app

from changes.backends.koality.builder import KoalityBuilder
from changes.config import db
from changes.constants import Result, Status
from changes.models import (
    Repository, Project, Build, Revision, Author, BuildPhase, BuildStep, Patch,
    RemoteEntity
)
from changes.testutils import BackendTestCase, SAMPLE_DIFF


class KoalityBuilderTestCase(BackendTestCase):
    builder_cls = KoalityBuilder
    builder_options = {
        'base_url': 'https://koality.example.com',
        'api_key': 'a' * 12,
        'project_id': 26,
    }
    provider = 'koality'

    def setUp(self):
        self.repo = Repository(url='https://github.com/dropbox/changes.git')
        self.project = Project(repository=self.repo, name='test', slug='test')
        self.project_entity = self.make_project_entity()

        db.session.add(self.repo)
        db.session.add(self.project)

    def get_builder(self):
        return self.builder_cls(app=current_app, **self.builder_options)

    def load_fixture(self, filename):
        filepath = os.path.join(
            os.path.dirname(__file__),
            filename,
        )
        with open(filepath, 'rb') as fp:
            return fp.read()

    def make_project_entity(self, project=None, data=None):
        return self.make_entity('project', (project or self.project).id, 1)


class SyncBuildTest(KoalityBuilderTestCase):
    # TODO(dcramer): we should break this up into testing individual methods
    # so edge cases can be more isolated
    @responses.activate
    def test_simple(self):
        responses.add(
            responses.GET, 'https://koality.example.com/api/v/0/repositories/1/changes/?key=aaaaaaaaaaaa',
            match_querystring=True,
            body=self.load_fixture('fixtures/GET/change_index.json'))

        responses.add(
            responses.GET, 'https://koality.example.com/api/v/0/repositories/1/changes/1?key=aaaaaaaaaaaa',
            match_querystring=True,
            body=self.load_fixture('fixtures/GET/change_details.json'))

        responses.add(
            responses.GET, 'https://koality.example.com/api/v/0/repositories/1/changes/1/stages?key=aaaaaaaaaaaa',
            match_querystring=True,
            body=self.load_fixture('fixtures/GET/change_stage_index.json'))

        backend = self.get_builder()
        change = self.create_change(self.project)
        build = self.create_build(project=self.project, change=change)

        entity = RemoteEntity(
            type='build',
            internal_id=build.id,
            provider=self.provider,
            remote_id='1',
            data={
                'project_id': 1,
                'change_id': 1,
            }
        )
        db.session.add(entity)

        backend.sync_build(
            build=build,
        )

        assert build.label == 'Fixing visual regression with visuals.'
        assert build.revision_sha == '7ebd1f2d750064652ef5bbff72452cc19e1731e0'
        assert build.status == Status.finished
        assert build.result == Result.failed
        assert build.date_started == datetime(2013, 9, 19, 22, 15, 22)
        assert build.date_finished == datetime(2013, 9, 19, 22, 15, 36)

        revision = Revision.query.filter_by(
            sha=build.revision_sha,
            repository=build.repository,
        )[0]
        author = Author.query.get(revision.author_id)
        build = Build.query.get(build.id)

        assert revision.message == 'Fixing visual regression with visuals.'

        assert author.email == 'john@example.com'
        assert author.name == 'John Developer'

        phase_list = list(BuildPhase.query.filter_by(
            build=build,
        ))

        phase_list.sort(key=lambda x: x.date_started)

        assert len(phase_list) == 3

        assert phase_list[0].project_id == build.project_id
        assert phase_list[0].repository_id == build.repository_id
        assert phase_list[0].label == 'Setup'
        assert phase_list[0].status == Status.finished
        assert phase_list[0].result == Result.passed
        assert phase_list[0].date_started == datetime(2013, 9, 19, 22, 15, 22)
        assert phase_list[0].date_finished == datetime(2013, 9, 19, 22, 15, 33)

        assert phase_list[1].project_id == build.project_id
        assert phase_list[1].repository_id == build.repository_id
        assert phase_list[1].label == 'Compile'
        assert phase_list[1].status == Status.finished
        assert phase_list[1].result == Result.passed
        assert phase_list[1].date_started == datetime(2013, 9, 19, 22, 15, 22, 500000)
        assert phase_list[1].date_finished == datetime(2013, 9, 19, 22, 15, 34)

        assert phase_list[2].project_id == build.project_id
        assert phase_list[2].repository_id == build.repository_id
        assert phase_list[2].label == 'Test'
        assert phase_list[2].status == Status.finished
        assert phase_list[2].result == Result.failed
        assert phase_list[2].date_started == datetime(2013, 9, 19, 22, 15, 25)
        assert phase_list[2].date_finished == datetime(2013, 9, 19, 22, 15, 36)

        step_list = list(BuildStep.query.filter_by(
            build=build,
        ))

        step_list.sort(key=lambda x: (x.date_started, x.date_created))

        assert len(step_list) == 6

        assert step_list[0].project_id == build.project_id
        assert step_list[0].repository_id == build.repository_id
        assert step_list[0].phase_id == phase_list[0].id
        assert step_list[0].label == 'ci/setup'
        assert step_list[0].status == Status.finished
        assert step_list[0].result == Result.passed
        assert step_list[0].date_started == datetime(2013, 9, 19, 22, 15, 22)
        assert step_list[0].date_finished == datetime(2013, 9, 19, 22, 15, 33)

        assert step_list[1].project_id == build.project_id
        assert step_list[1].repository_id == build.repository_id
        assert step_list[1].phase_id == phase_list[0].id
        assert step_list[1].label == 'ci/setup'
        assert step_list[1].status == Status.finished
        assert step_list[1].result == Result.passed
        assert step_list[1].date_started == datetime(2013, 9, 19, 22, 15, 22)
        assert step_list[1].date_finished == datetime(2013, 9, 19, 22, 15, 33)

        assert step_list[2].project_id == build.project_id
        assert step_list[2].repository_id == build.repository_id
        assert step_list[2].phase_id == phase_list[1].id
        assert step_list[2].label == 'ci/compile'
        assert step_list[2].status == Status.finished
        assert step_list[2].result == Result.passed
        assert step_list[2].date_started == datetime(2013, 9, 19, 22, 15, 22, 500000)
        assert step_list[2].date_finished == datetime(2013, 9, 19, 22, 15, 33, 500000)

        assert step_list[3].project_id == build.project_id
        assert step_list[3].repository_id == build.repository_id
        assert step_list[3].phase_id == phase_list[1].id
        assert step_list[3].label == 'ci/compile'
        assert step_list[3].status == Status.finished
        assert step_list[3].result == Result.passed
        assert step_list[3].date_started == datetime(2013, 9, 19, 22, 15, 23)
        assert step_list[3].date_finished == datetime(2013, 9, 19, 22, 15, 34)

        assert step_list[4].project_id == build.project_id
        assert step_list[4].repository_id == build.repository_id
        assert step_list[4].phase_id == phase_list[2].id
        assert step_list[4].label == 'ci/test'
        assert step_list[4].status == Status.finished
        assert step_list[4].result == Result.passed
        assert step_list[4].date_started == datetime(2013, 9, 19, 22, 15, 25)
        assert step_list[4].date_finished == datetime(2013, 9, 19, 22, 15, 35)

        assert step_list[5].project_id == build.project_id
        assert step_list[5].repository_id == build.repository_id
        assert step_list[5].phase_id == phase_list[2].id
        assert step_list[5].label == 'ci/test'
        assert step_list[5].status == Status.finished
        assert step_list[5].result == Result.failed
        assert step_list[5].date_started == datetime(2013, 9, 19, 22, 15, 26)
        assert step_list[5].date_finished == datetime(2013, 9, 19, 22, 15, 36)


class CreateBuildTest(KoalityBuilderTestCase):
    @responses.activate
    def test_simple(self):
        responses.add(
            responses.POST, 'https://koality.example.com/api/v/0/repositories/1/changes',
            body=self.load_fixture('fixtures/POST/change_index.json'))

        backend = self.get_builder()

        revision = '7ebd1f2d750064652ef5bbff72452cc19e1731e0'

        build = Build(
            repository=self.repo,
            project=self.project,
            revision_sha=revision,
            label='D1345',
        )
        db.session.add(build)

        entity = backend.create_build(
            build=build,
        )

        assert entity.type == 'build'
        assert entity.internal_id == build.id
        assert entity.remote_id == '1501'
        assert entity.provider == 'koality'
        assert entity.data == {
            'project_id': 1,
            'change_id': 1501,
        }

        assert len(responses.calls) == 1

        call = responses.calls[0]

        # TODO(dcramer): this is a pretty gross testing api
        assert 'sha={0}'.format(revision) in call.request.body
        assert 'email=' in call.request.body

    @responses.activate
    def test_patch(self):
        responses.add(
            responses.POST, 'https://koality.example.com/api/v/0/repositories/1/changes',
            body=self.load_fixture('fixtures/POST/change_index.json'))

        backend = self.get_builder()

        revision = '7ebd1f2d750064652ef5bbff72452cc19e1731e0'

        patch = Patch(
            repository=self.repo,
            project=self.project,
            parent_revision_sha=revision,
            label='D1345',
            diff=SAMPLE_DIFF,
        )
        db.session.add(patch)

        build = Build(
            repository=self.repo,
            project=self.project,
            revision_sha=revision,
            patch=patch,
            label='D1345',
        )
        db.session.add(build)

        entity = backend.create_build(
            build=build,
        )
        assert entity.type == 'build'
        assert entity.internal_id == build.id
        assert entity.remote_id == '1501'
        assert entity.provider == 'koality'
        assert entity.data == {
            'project_id': 1,
            'change_id': 1501,
        }

        assert len(responses.calls) == 1

        # call = responses.calls[0]

        # print call.request.body

        # # TODO(dcramer): this is a pretty gross testing api
        # assert 'Content-Disposition: form-data; name="sha"\r\n\r\n{0}'.format(revision) in call.request.body
        # assert 'Content-Disposition: form-data; name="patch"; filename="patch"\r\nContent-Type: application/octet-stream\r\n\r\n{0}'.format(SAMPLE_DIFF) in call.request.body

    @responses.activate
    def test_without_entity(self):
        responses.add(
            responses.POST, 'https://koality.example.com/api/v/0/repositories/26/changes',
            body=self.load_fixture('fixtures/POST/change_index.json'))

        backend = self.get_builder()

        revision = '7ebd1f2d750064652ef5bbff72452cc19e1731e0'

        build = Build(
            repository=self.repo,
            project=self.create_project(),
            revision_sha=revision,
            label='D1345',
        )
        db.session.add(build)

        entity = backend.create_build(
            build=build,
        )

        assert entity.type == 'build'
        assert entity.internal_id == build.id
        assert entity.remote_id == '1501'
        assert entity.provider == 'koality'
        assert entity.data == {
            'project_id': 26,
            'change_id': 1501,
        }
