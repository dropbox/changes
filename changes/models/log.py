import uuid

from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, String, Text, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.schema import Index, UniqueConstraint

from changes.config import db
from changes.db.types.guid import GUID


class LogSource(db.Model):
    __tablename__ = 'logsource'
    __table_args__ = (
        UniqueConstraint('build_id', 'name', name='unq_logsource_key'),
        Index('idx_build_project_id', 'project_id'),
    )

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    build_id = Column(GUID, ForeignKey('build.id'), nullable=False)
    project_id = Column(GUID, ForeignKey('project.id'), nullable=False)
    name = Column(String(64), nullable=False)
    date_created = Column(DateTime, default=datetime.utcnow)

    build = relationship('Build')
    project = relationship('Project')

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
        Index('idx_logchunk_build_id', 'build_id'),
        Index('idx_logchunk_source_id', 'source_id'),
        UniqueConstraint('source_id', 'offset', name='unq_logchunk_source_offset'),
    )

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    build_id = Column(GUID, ForeignKey('build.id'), nullable=False)
    project_id = Column(GUID, ForeignKey('project.id'), nullable=False)
    source_id = Column(GUID, ForeignKey('logsource.id'), nullable=False)
    # offset is sum(c.size for c in chunks_before_this)
    offset = Column(Integer, nullable=False)
    # size is len(text)
    size = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    date_created = Column(DateTime, default=datetime.utcnow)

    build = relationship('Build')
    project = relationship('Project')
    source = relationship('LogSource')

    def __init__(self, **kwargs):
        super(LogChunk, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid.uuid4()
        if self.date_created is None:
            self.date_created = datetime.utcnow()
