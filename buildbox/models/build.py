import uuid

from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, ForeignKey

from buildbox.db.base import Base
from buildbox.db.types.guid import GUID


class BuildStatus(object):
    UNKNOWN = 0
    QUEUED = 1
    INPROGRESS = 2
    PASSED = 3
    FAILED = 4


class Build(Base):
    __tablename__ = 'build'

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    repository_id = Column(GUID, ForeignKey('repository.id'), nullable=False)
    project_id = Column(GUID, ForeignKey('project.id'), nullable=False)
    parent_revision_id = Column(GUID, ForeignKey('revision.id'), nullable=False)
    status = Column(Integer, nullable=False, default=0)
    date_started = Column(DateTime)
    date_finished = Column(DateTime)
    date_created = Column(DateTime, default=datetime.utcnow)
