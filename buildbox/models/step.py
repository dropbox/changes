import uuid

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey

from buildbox.db.base import Base
from buildbox.db.types.guid import GUID


class StepStatus(object):
    UNKNOWN = 0
    QUEUED = 1
    INPROGRESS = 2
    PASSED = 3
    FAILED = 4


class Step(Base):
    __tablename__ = 'step'

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    phase_id = Column(GUID, ForeignKey('phase.id'), primary_key=True)
    build_id = Column(GUID, ForeignKey('build.id'), nullable=False)
    repository_id = Column(GUID, ForeignKey('repository.id'), nullable=False)
    project_id = Column(GUID, ForeignKey('project.id'), nullable=False)
    label = Column(String(128), nullable=False)
    status = Column(Integer, nullable=False, default=0)
    date_started = Column(DateTime)
    date_finished = Column(DateTime)
    date_created = Column(DateTime, default=datetime.utcnow)
