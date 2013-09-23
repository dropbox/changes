from unittest2 import TestCase

from buildbox.models import RemoteEntity


class BackendTestCase(TestCase):
    backend_cls = None
    backend_options = {}
    provider = None

    def get_backend(self):
        return self.backend_cls(**self.backend_options)

    def make_entity(self, type, internal_id, remote_id):
        entity = RemoteEntity(
            type=type,
            remote_id=remote_id,
            internal_id=internal_id,
            provider=self.provider,
        )
        with self.get_backend().get_session() as session:
            session.add(entity)
        return entity
