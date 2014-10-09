from __future__ import absolute_import

from datetime import datetime
from uuid import uuid4
from enum import Enum

from sqlalchemy import Column, DateTime, ForeignKey
from sqlalchemy.orm import backref, relationship
from sqlalchemy.schema import UniqueConstraint

from changes.config import db
from changes.db.types.enum import Enum as EnumType
from changes.db.types.guid import GUID


class SnapshotStatus(Enum):
    unknown = 0
    active = 1
    failed = 2
    invalidated = 3
    pending = 4

    def __str__(self):
        return STATUS_LABELS[self]


STATUS_LABELS = {
    SnapshotStatus.unknown: 'Unknown',
    SnapshotStatus.pending: 'Pending',
    SnapshotStatus.active: 'Active',
    SnapshotStatus.failed: 'Failed',
    SnapshotStatus.invalidated: 'Invalidated',
}


class Snapshot(db.Model):
    """
    Represents a snapshot used as a base in builds.

    This is primarily used to indicate status and contains a collection of
    SnapshotImage's.
    """

    __tablename__ = 'snapshot'

    id = Column(GUID, primary_key=True, default=uuid4)
    project_id = Column(
        GUID, ForeignKey('project.id', ondelete="CASCADE"), nullable=False)
    build_id = Column(GUID, ForeignKey('build.id'), unique=True)
    source_id = Column(GUID, ForeignKey('source.id'))
    status = Column(EnumType(SnapshotStatus),
                    default=SnapshotStatus.unknown,
                    nullable=False, server_default='0')
    date_created = Column(DateTime, default=datetime.utcnow, nullable=False)

    build = relationship('Build')
    project = relationship('Project', innerjoin=True)
    source = relationship('Source')

    def __init__(self, **kwargs):
        super(Snapshot, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid4()

    @classmethod
    def get_current(self, project_id):
        from changes.models import ProjectOption

        current_id = db.session.query(ProjectOption.value).filter(
            ProjectOption.project_id == project_id,
            ProjectOption.name == 'snapshot.current',
        ).scalar()
        if not current_id:
            return

        return Snapshot.query.get(current_id)


class SnapshotImage(db.Model):
    """
    Represents an individual image within a snapshot.

    An image is bound to a (snapshot, plan) and represents the low level base
    image that a snapshottable-job should be based on.
    """

    __tablename__ = 'snapshot_image'
    __table_args__ = (
        UniqueConstraint('snapshot_id', 'plan_id', name='unq_snapshotimage_plan'),
    )

    id = Column(GUID, primary_key=True, default=uuid4)
    snapshot_id = Column(
        GUID, ForeignKey('snapshot.id', ondelete="CASCADE"), nullable=False)
    plan_id = Column(
        GUID, ForeignKey('plan.id', ondelete="CASCADE"), nullable=False)
    job_id = Column(GUID, ForeignKey('job.id', ondelete="CASCADE"), unique=True)
    status = Column(EnumType(SnapshotStatus),
                    default=SnapshotStatus.unknown,
                    nullable=False, server_default='0')
    date_created = Column(DateTime, default=datetime.utcnow, nullable=False)

    snapshot = relationship('Snapshot', backref=backref('images', order_by='SnapshotImage.date_created'))
    plan = relationship('Plan')
    job = relationship('Job')

    def __init__(self, **kwargs):
        super(SnapshotImage, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid4()
