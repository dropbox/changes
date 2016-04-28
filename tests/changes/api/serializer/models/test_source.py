from datetime import datetime

from changes.api.serializer import serialize
from changes.config import db
from changes.models.source import Source
from changes.testutils import TestCase


class SourceCrumblerTest(TestCase):
    def test_simple(self):
        repo = self.create_repo()
        revision = self.create_revision(repository=repo)
        source = Source(
            repository=repo,
            repository_id=repo.id,
            revision=revision,
            revision_sha=revision.sha,
            date_created=datetime(2013, 9, 19, 22, 15, 22),
        )
        db.session.add(source)
        result = serialize(source)
        assert result['id'] == source.id.hex
        assert result['dateCreated'] == '2013-09-19T22:15:22'
        assert result['revision']['id'] == revision.sha

    def test_phabricator_links(self):
        repo = self.create_repo()
        revision = self.create_revision(repository=repo)
        project = self.create_project(repository=repo)
        source = self.create_source(
            project=project,
            revision_sha=revision.sha,
            date_created=datetime(2013, 9, 19, 22, 15, 22),
            patch=self.create_patch(repository=repo),
            data={
                'phabricator.callsign': 'FOO',
                'phabricator.diffID': '1324134',
                'phabricator.revisionID': '1234',
                'phabricator.revisionURL': 'https://phabricator.example.com/D1234',
            }
        )
        db.session.add(source)
        result = serialize(source)

        assert result['patch']['external'] == {
            'label': 'D1234',
            'link': 'https://phabricator.example.com/D1234',
        }
