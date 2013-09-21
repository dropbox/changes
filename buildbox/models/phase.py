import uuid

from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey

from buildbox.constants import Status, Result
from buildbox.db.base import Base
from buildbox.db.types.enum import Enum
from buildbox.db.types.guid import GUID


class Phase(Base):
    __tablename__ = 'phase'

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    build_id = Column(GUID, ForeignKey('build.id'), nullable=False)
    repository_id = Column(GUID, ForeignKey('repository.id'), nullable=False)
    project_id = Column(GUID, ForeignKey('project.id'), nullable=False)
    label = Column(String(128), nullable=False)
    status = Column(Enum(Status), nullable=False, default=0)
    result = Column(Enum(Result), nullable=False, default=0)
    date_started = Column(DateTime)
    date_finished = Column(DateTime)
    date_created = Column(DateTime, default=datetime.utcnow)
