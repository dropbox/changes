import uuid

from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, String, Text, Integer
from sqlalchemy.orm import backref, relationship
from sqlalchemy.schema import Index, UniqueConstraint

from changes.config import db
from changes.db.types.guid import GUID


LOG_CHUNK_SIZE = 4096


class LogSource(db.Model):
    __tablename__ = 'logsource'
    __table_args__ = (
        UniqueConstraint('step_id', 'name', name='unq_logsource_key2'),
        Index('idx_build_project_id', 'project_id'),
    )

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    job_id = Column(GUID, ForeignKey('job.id', ondelete="CASCADE"), nullable=False)
    project_id = Column(GUID, ForeignKey('project.id', ondelete="CASCADE"), nullable=False)
    step_id = Column(GUID, ForeignKey('jobstep.id', ondelete="CASCADE"))
    name = Column(String(64), nullable=False)
    date_created = Column(DateTime, default=datetime.utcnow)

    job = relationship('Job')
    project = relationship('Project')
    step = relationship('JobStep', backref=backref('logsources', order_by='LogSource.date_created'))

    def __init__(self, **kwargs):
        super(LogSource, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid.uuid4()
        if self.date_created is None:
            self.date_created = datetime.utcnow()


class LogChunk(db.Model):
    __tablename__ = 'logchunk'
    __table_args__ = (
        Index('idx_logchunk_project_id', 'project_id'),
        Index('idx_logchunk_build_id', 'job_id'),
        Index('idx_logchunk_source_id', 'source_id'),
        UniqueConstraint('source_id', 'offset', name='unq_logchunk_source_offset'),
    )

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    job_id = Column(GUID, ForeignKey('job.id', ondelete="CASCADE"), nullable=False)
    project_id = Column(GUID, ForeignKey('project.id', ondelete="CASCADE"), nullable=False)
    source_id = Column(GUID, ForeignKey('logsource.id', ondelete="CASCADE"), nullable=False)
    # offset is sum(c.size for c in chunks_before_this)
    offset = Column(Integer, nullable=False)
    # size is len(text)
    size = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    date_created = Column(DateTime, default=datetime.utcnow)

    job = relationship('Job')
    project = relationship('Project')
    source = relationship('LogSource')

    def __init__(self, **kwargs):
        super(LogChunk, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid.uuid4()
        if self.date_created is None:
            self.date_created = datetime.utcnow()
