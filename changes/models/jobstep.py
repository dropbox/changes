import uuid

from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship, backref
from sqlalchemy.schema import Index

from changes.config import db
from changes.constants import Status, Result
from changes.db.utils import model_repr
from changes.db.types.enum import Enum
from changes.db.types.guid import GUID
from changes.db.types.json import JSONEncodedDict


class FutureJobStep(object):
    def __init__(self, label, commands=None, data=None):
        self.label = label
        self.commands = commands or []
        self.data = data or {}

    def as_jobstep(self, jobphase):
        return JobStep(
            job_id=jobphase.job_id,
            phase=jobphase,
            phase_id=jobphase.id,
            project_id=jobphase.project_id,
            label=self.label,
            status=Status.queued,
            data=self.data,
        )


class JobStep(db.Model):
    """
    The most granular unit of work; run on a particular node, has a status and
    a result.
    """
    __tablename__ = 'jobstep'

    __table_args__ = (
            Index('idx_jobstep_status', 'status'),
            Index('idx_jobstep_cluster', 'cluster'),
    )

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    job_id = Column(GUID, ForeignKey('job.id', ondelete="CASCADE"), nullable=False)
    phase_id = Column(GUID, ForeignKey('jobphase.id', ondelete="CASCADE"), nullable=False)
    project_id = Column(GUID, ForeignKey('project.id', ondelete="CASCADE"), nullable=False)
    label = Column(String(128), nullable=False)
    status = Column(Enum(Status), nullable=False, default=Status.unknown)
    result = Column(Enum(Result), nullable=False, default=Result.unknown)
    node_id = Column(GUID, ForeignKey('node.id', ondelete="CASCADE"))
    # id of JobStep that replaces this JobStep. Usually None, unless a JobStep
    # fails and is retried.
    replacement_id = Column(GUID, ForeignKey('jobstep.id', ondelete="CASCADE"), unique=True)
    # Used (for non-Jenkins builds) in jobstep_allocate to only allocate jobsteps
    # to slaves of a particular cluster. For Jenkins builds, this is pure documentation (typically
    # set to the Jenkins label), but should be accurate just the same.
    cluster = Column(String(128), nullable=True)
    date_started = Column(DateTime)
    date_finished = Column(DateTime)
    date_created = Column(DateTime, default=datetime.utcnow)
    last_heartbeat = Column(DateTime)
    data = Column(JSONEncodedDict)

    job = relationship('Job')
    project = relationship('Project')
    node = relationship('Node')
    phase = relationship('JobPhase', backref=backref('steps', order_by='JobStep.date_started'))

    __repr__ = model_repr('label')

    def __init__(self, **kwargs):
        super(JobStep, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid.uuid4()
        if self.result is None:
            self.result = Result.unknown
        if self.status is None:
            self.status = Status.unknown
        if self.date_created is None:
            self.date_created = datetime.utcnow()
        if self.data is None:
            self.data = {}

    @property
    def duration(self):
        """
        Return the duration (in milliseconds) that this item was in-progress.
        """
        if self.date_started and self.date_finished:
            duration = (self.date_finished - self.date_started).total_seconds() * 1000
        else:
            duration = None
        return duration
