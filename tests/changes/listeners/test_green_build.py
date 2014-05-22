from __future__ import absolute_import

import mock
import responses

from changes.constants import Result
from changes.listeners.green_build import build_finished_handler
from changes.models import Event, EventType, RepositoryBackend
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

        source = self.create_source(
            project=project,
            revision_sha='a' * 40,
        )
        build = self.create_build(
            project=project,
            source=source,
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
            'log', '-r aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', '--limit=1',
            '--template={rev}:{node|short}'
        ])

        get_options.assert_called_once_with(build.project_id)

        assert len(responses.calls) == 1
        assert responses.calls[0].request.url == 'https://foo.example.com/'
        assert responses.calls[0].request.body == 'project={project_slug}&build_server=changes&build_url=http%3A%2F%2Fexample.com%2Fprojects%2F{project_slug}%2Fbuilds%2F{build_id}%2F&id=134%3Aasdadfadf'.format(
            project_slug=build.project.slug,
            build_id=build.id.hex,
        )

        event = Event.query.filter(
            Event.type == EventType.green_build,
        ).first()
        assert event
        assert event.item_id == build.id
