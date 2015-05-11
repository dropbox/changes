from __future__ import absolute_import

import mock
import responses
import urlparse
from uuid import uuid4

from changes.constants import Result
from changes.listeners.green_build import build_finished_handler, \
    _set_latest_green_build_for_each_branch
from changes.models import Event, EventType, RepositoryBackend
from changes.models.latest_green_build import LatestGreenBuild
from changes.testutils import TestCase


class GreenBuildTest(TestCase):
    @responses.activate
    @mock.patch('changes.listeners.green_build.get_options')
    @mock.patch('changes.models.Repository.get_vcs')
    def test_simple(self, vcs, get_options):
        responses.add(responses.POST, 'https://foo.example.com')

        repository = self.create_repo(
            backend=RepositoryBackend.hg,
        )

        project = self.create_project(repository=repository)

        sha = uuid4().hex
        source = self.create_source(
            project=project,
            revision_sha=sha,
            revision=self.create_revision(repository=repository,
                                          branches=['default'],
                                          sha=sha
            )
        )

        build = self.create_build(
            project=project,
            source=source,
        )

        get_options.return_value = {
            'green-build.notify': '1',
        }
        vcs = build.source.repository.get_vcs.return_value
        vcs.run.return_value = '134:asdadfadf'

        # test with failing build
        build.result = Result.failed

        build_finished_handler(build_id=build.id.hex)

        assert len(responses.calls) == 0

        # test with passing build
        build.result = Result.passed

        build_finished_handler(build_id=build.id.hex)

        vcs.run.assert_called_once_with([
            'log', '-r %s' % sha, '--limit=1',
            '--template={rev}:{node|short}'
        ])

        get_options.assert_called_once_with(build.project_id)

        assert len(responses.calls) == 1
        assert responses.calls[0].request.url == 'https://foo.example.com/'

        body = urlparse.parse_qs(responses.calls[0].request.body)
        assert body['project'][0] == build.project.slug
        assert body['build_server'][0] == 'changes'
        assert body['build_url'][0] == "http://example.com/projects/%s/builds/%s/" % (build.project.slug, build.id.hex)
        assert body['id'][0] == '134:asdadfadf'
        assert 'author_name' in body
        assert 'author_email' in body
        assert 'revision_message' in body
        assert 'commit_timestamp' in body

        event = Event.query.filter(
            Event.type == EventType.green_build,
        ).first()
        assert event
        assert event.item_id == build.id

    @responses.activate
    @mock.patch('changes.models.Repository.get_vcs')
    def test_latest_green_build(self, vcs):
        repository = self.create_repo(
            backend=RepositoryBackend.hg,
        )
        project = self.create_project(repository=repository)

        child_sha = uuid4().hex
        source = self.create_source(
            project=project,
            revision_sha=child_sha,
            revision=self.create_revision(repository=repository,
                                          branches=['default'],
                                          sha=child_sha
            )
        )
        build_parent = self.create_build(
            project=project,
            label="parent"
        )

        build_child = self.create_build(
            project=project,
            source=source,
            label="child"
        )

        def is_child_parent(child_in_question, parent_in_question):
            return child_in_question == child_sha

        vcs.is_child_parent.side_effect = is_child_parent

        current_latest_green_build = self.create_latest_green_build(project=project,
                                                                    build=build_parent,
                                                                    branch='default')

        assert current_latest_green_build.build == build_parent
        _set_latest_green_build_for_each_branch(build_child, source, vcs)

        # vcs.is_child_parent.return_value
        new_latest_green = LatestGreenBuild.query.filter(
            LatestGreenBuild.project_id == project.id,
            LatestGreenBuild.branch == 'default').first()
        assert new_latest_green.build == build_child
