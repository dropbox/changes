import uuid

from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship, backref
from sqlalchemy.schema import UniqueConstraint

from changes.config import db
from changes.constants import Status, Result
from changes.db.types.enum import Enum
from changes.db.types.guid import GUID


class BuildPhase(db.Model):
    """
    A build phase represents a grouping of jobs.

    For example, a common situation for a build is that it has a "test" and a
    "release" phase. In this case, we'd have one or more jobs under test, and
    one or more jobs under release. These test jobs may be things like "Windows"
    and "Linux", whereas the release may simply be "Upload Tarball".

    The build phase represents the aggregate result of all jobs under it.
    """
    __tablename__ = 'buildphase'
    __table_args__ = (
        UniqueConstraint('build_id', 'label', name='unq_buildphase_key'),
    )

    id = Column(GUID, nullable=False, primary_key=True, default=uuid.uuid4)
    build_id = Column(GUID, ForeignKey('build.id', ondelete="CASCADE"), nullable=False)
    project_id = Column(GUID, ForeignKey('project.id', ondelete="CASCADE"), nullable=False)
    label = Column(String(128), nullable=False)
    status = Column(Enum(Status), nullable=False, default=Status.unknown,
                    server_default='0')
    result = Column(Enum(Result), nullable=False, default=Result.unknown,
                    server_default='0')
    order = Column(Integer, nullable=False, default=0, server_default='0')
    duration = Column(Integer)
    date_started = Column(DateTime)
    date_finished = Column(DateTime)
    date_created = Column(DateTime, default=datetime.utcnow, nullable=False,
                          server_default='now()')

    build = relationship('Build', backref=backref('phases', order_by='BuildPhase.date_started'))
    project = relationship('Project')

    def __init__(self, **kwargs):
        super(BuildPhase, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid.uuid4()
        if self.result is None:
            self.result = Result.unknown
        if self.status is None:
            self.status = Status.unknown
        if self.date_created is None:
            self.date_created = datetime.utcnow()
        if self.date_started and self.date_finished and not self.duration:
            self.duration = (self.date_finished - self.date_started).total_seconds() * 1000
