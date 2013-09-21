import uuid

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey

from buildbox.db.base import Base
from buildbox.db.types.guid import GUID


class PhaseStatus(object):
    UNKNOWN = 0
    QUEUED = 1
    INPROGRESS = 2
    PASSED = 3
    FAILED = 4


class Phase(Base):
    __tablename__ = 'phase'

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    build_id = Column(GUID, ForeignKey('build.id'), nullable=False)
    repository_id = Column(GUID, ForeignKey('repository.id'), nullable=False)
    project_id = Column(GUID, ForeignKey('project.id'), nullable=False)
    label = Column(String(128), nullable=False)
    status = Column(Integer, nullable=False, default=0)
    date_started = Column(DateTime)
    date_finished = Column(DateTime)
    date_created = Column(DateTime, default=datetime.utcnow)
