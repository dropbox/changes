import uuid

from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, String

from buildbox.constants import Status, Result
from buildbox.db.base import Base
from buildbox.db.types.enum import Enum
from buildbox.db.types.guid import GUID


class Build(Base):
    __tablename__ = 'build'

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    repository_id = Column(GUID, ForeignKey('repository.id'), nullable=False)
    project_id = Column(GUID, ForeignKey('project.id'), nullable=False)
    parent_revision_sha = Column(String(40), nullable=False)
    label = Column(String(64), nullable=False)
    status = Column(Enum(Status), nullable=False, default=0)
    result = Column(Enum(Result), nullable=False, default=0)
    date_started = Column(DateTime)
    date_finished = Column(DateTime)
    date_created = Column(DateTime, default=datetime.utcnow)

    @property
    def duration(self):
        if self.date_started and self.date_finished:
            duration = self.date_finished - self.date_started
        else:
            duration = None
        return duration
