import uuid

from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, String, Integer
from sqlalchemy.orm import backref, relationship
from sqlalchemy.schema import Index, UniqueConstraint

from changes.config import db
from changes.constants import Status, Result
from changes.db.types.enum import Enum
from changes.db.types.guid import GUID
from changes.db.types.json import JSONEncodedDict
from changes.db.utils import model_repr


class Job(db.Model):
    __tablename__ = 'job'
    __table_args__ = (
        Index('idx_build_project_id', 'project_id'),
        Index('idx_build_change_id', 'change_id'),
        Index('idx_build_source_id', 'source_id'),
        Index('idx_build_family_id', 'build_id'),
        UniqueConstraint('build_id', 'number', name='unq_job_number'),
    )

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    number = Column(Integer)
    # TODO(dcramer): change should be removed in favor of an m2m between
    # Change and Source
    build_id = Column(GUID, ForeignKey('build.id', ondelete="CASCADE"))
    change_id = Column(GUID, ForeignKey('change.id', ondelete="CASCADE"))
    project_id = Column(GUID, ForeignKey('project.id', ondelete="CASCADE"), nullable=False)
    source_id = Column(GUID, ForeignKey('source.id', ondelete="CASCADE"))
    label = Column(String(128), nullable=False)
    status = Column(Enum(Status), nullable=False, default=Status.unknown)
    result = Column(Enum(Result), nullable=False, default=Result.unknown)
    duration = Column(Integer)
    date_started = Column(DateTime)
    date_finished = Column(DateTime)
    date_created = Column(DateTime, default=datetime.utcnow)
    date_modified = Column(DateTime, default=datetime.utcnow)
    data = Column(JSONEncodedDict)

    change = relationship('Change')
    build = relationship('Build', backref=backref('jobs', order_by='Job.number'))
    project = relationship('Project')
    source = relationship('Source')

    __repr__ = model_repr('label', 'target')

    def __init__(self, **kwargs):
        super(Job, self).__init__(**kwargs)
        if self.data is None:
            self.data = {}
        if self.id is None:
            self.id = uuid.uuid4()
        if self.result is None:
            self.result = Result.unknown
        if self.status is None:
            self.status = Status.unknown
        if self.date_created is None:
            self.date_created = datetime.utcnow()
        if self.date_modified is None:
            self.date_modified = self.date_created
        if self.date_started and self.date_finished and not self.duration:
            self.duration = (self.date_finished - self.date_started).total_seconds() * 1000
