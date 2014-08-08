from __future__ import absolute_import

from uuid import uuid4
from enum import Enum

from sqlalchemy import Column, ForeignKey
from sqlalchemy.orm import relationship

from changes.config import db
from changes.db.types.enum import Enum as EnumType
from changes.db.types.guid import GUID


class SnapshotStatus(Enum):
    unknown = 0
    active = 1
    failed = 2
    invalidated = 3

    def __str__(self):
        return STATUS_LABELS[self]


STATUS_LABELS = {
    SnapshotStatus.unknown: 'unknown',
    SnapshotStatus.active: 'active',
    SnapshotStatus.failed: 'failed',
    SnapshotStatus.invalidated: 'invalidated',
}


class Snapshot(db.Model):
    """
    Represents a snapshot used as a base in builds.

    This is primarily used to indicate status.
    """

    __tablename__ = 'snapshot'
    __table_args__ = (
    )

    id = Column(GUID, primary_key=True, default=uuid4)
    project_id = Column(
        GUID, ForeignKey('project.id', ondelete="CASCADE"), nullable=False)
    build_id = Column(GUID, ForeignKey('build.id'))
    status = Column(EnumType(SnapshotStatus),
                    default=SnapshotStatus.unknown,
                    nullable=False, server_default='0')

    build = relationship('Build')
    project = relationship('Project', innerjoin=True)

    def __init__(self, **kwargs):
        super(Snapshot, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid4()
