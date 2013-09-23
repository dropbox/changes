import enum
import uuid

from datetime import datetime
from sqlalchemy import Column, DateTime, String, UniqueConstraint

from buildbox.db.base import Base
from buildbox.db.types.enum import Enum
from buildbox.db.types.guid import GUID
from buildbox.db.types.json import JSONEncodedDict


class EntityType(enum.Enum):
    project = 1
    build = 2
    phase = 3
    step = 4
    node = 5

    @property
    def model(self):
        if self == EntityType.project:
            from buildbox.models import Project
            return Project
        elif self == EntityType.build:
            from buildbox.models import Build
            return Build
        elif self == EntityType.phase:
            from buildbox.models import Phase
            return Phase
        elif self == EntityType.step:
            from buildbox.models import Step
            return Step
        elif self == EntityType.node:
            from buildbox.models import Node
            return Node


class RemoteEntity(Base):
    __tablename__ = 'remoteentity'
    __table_args__ = (
        UniqueConstraint('provider', 'remote_id', 'type', name='remote_identifier'),
    )

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    type = Column(Enum(EntityType))
    provider = Column(String(128))
    remote_id = Column(String(128), nullable=False)
    internal_id = Column(GUID, nullable=False, unique=True)
    data = Column(JSONEncodedDict)
    date_created = Column(DateTime, default=datetime.utcnow)
