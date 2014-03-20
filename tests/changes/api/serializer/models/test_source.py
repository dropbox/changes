from datetime import datetime

from changes.api.serializer import serialize
from changes.config import db
from changes.models import Source
from changes.testutils import TestCase


class SourceSerializerTest(TestCase):
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
