
from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship
from sqlalchemy.schema import UniqueConstraint
from uuid import uuid4

from changes.config import db
from changes.db.types.guid import GUID


class Source(db.Model):
    """
    A source represents the canonical parameters that a build is running against.

    It always implies a revision to build off (though until we have full repo
    integration this is considered optional, and defaults to tip/master), and
    an optional patch_id to apply on top of it.
    """
    id = Column(GUID, primary_key=True, default=uuid4)
    repository_id = Column(GUID, ForeignKey('repository.id'), nullable=False)
    patch_id = Column(GUID, ForeignKey('patch.id'))
    revision_sha = Column(String(40))
    date_created = Column(DateTime, default=datetime.utcnow)

    repository = relationship('Repository')
    patch = relationship('Patch')

    __tablename__ = 'source'
    __table_args__ = (
        UniqueConstraint(
            'repository_id', 'revision_sha', name='unq_source_revision',
            postgresql_where=(patch_id == None)),  # NOQA
        UniqueConstraint(
            'patch_id', name='unq_source_patch_id',
            postgresql_where=(patch_id != None)),  # NOQA
    )

    def __init__(self, **kwargs):
        super(Source, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid4()
        if self.date_created is None:
            self.date_created = datetime.utcnow()
