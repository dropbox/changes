import uuid

from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text, Integer
from sqlalchemy.orm import backref, relationship
from sqlalchemy.schema import Index, UniqueConstraint

from changes.config import db
from changes.db.types.guid import GUID

# The expected maximum log chunk size; chunks from incremental logs
# and final chunks can certainly be smaller.
LOG_CHUNK_SIZE = 4096 * 2


class LogSource(db.Model):
    """
    We log the console output for each jobstep. logsource is an
    entity table for these "logfiles". logchunk contains the actual text.

    If we're using artifact store to store/host the log file, in_artifact_store will be set to true.
    No logchunk entries will be associated with such logsources.
    """
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
    in_artifact_store = Column(Boolean, default=False)

    job = relationship('Job')
    project = relationship('Project')
    step = relationship('JobStep', backref=backref('logsources', order_by='LogSource.date_created'))

    def __init__(self, **kwargs):
        super(LogSource, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid.uuid4()
        if self.date_created is None:
            self.date_created = datetime.utcnow()

    def is_infrastructural(self):
        """
        Returns:
            bool: Whether this LogSource is for an infrastructural log.

        """
        # We only have one infrastructural log at the moment, and it's always named infralog.
        return self.name == "infralog"

    def get_url(self):
        """
           Returns:
                str: The relative URI on Changes at which this log can be viewed.
        """
        # TODO(kylec): Bad to have this UI knowledge in model code, but convenient.
        job = self.job
        build = job.build
        project = build.project
        return "/projects/{}/builds/{}/jobs/{}/logs/{}/".format(
                project.slug, build.id.hex, job.id.hex, self.id.hex)


class LogChunk(db.Model):
    """
    Chunks of text. Each row in logchunk is associated with a particular
    logsource entry, and has an offset and blob of text. By grabbing all
    logchunks for a given logsource id, you can combine them to get the
    full log.
    """
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
