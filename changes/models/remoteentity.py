import enum
import uuid

from datetime import datetime
from sqlalchemy import Column, DateTime, String, UniqueConstraint

from changes.config import db
from changes.db.types.enum import Enum
from changes.db.types.guid import GUID
from changes.db.types.json import JSONEncodedDict


class EntityType(enum.Enum):
    project = 1
    build = 2
    phase = 3
    step = 4
    node = 5
    change = 6
    patch = 7

    @property
    def model(self):
        if self == EntityType.project:
            from changes.models import Project
            return Project
        elif self == EntityType.build:
            from changes.models import Build
            return Build
        elif self == EntityType.phase:
            from changes.models import Phase
            return Phase
        elif self == EntityType.step:
            from changes.models import Step
            return Step
        elif self == EntityType.node:
            from changes.models import Node
            return Node
        elif self == EntityType.change:
            from changes.models import Change
            return Change
        elif self == EntityType.patch:
            from changes.models import Patch
            return Patch


class RemoteEntity(db.Model):
    __tablename__ = 'remoteentity'
    __table_args__ = (
        UniqueConstraint('provider', 'remote_id', 'type', name='remote_identifier'),
    )

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    type = Column(Enum(EntityType), nullable=False)
    provider = Column(String(128), nullable=False)
    remote_id = Column(String(128), nullable=False)
    internal_id = Column(GUID, nullable=False)
    data = Column(JSONEncodedDict, default=dict)
    date_created = Column(DateTime, default=datetime.utcnow)

    def __init__(self, **kwargs):
        super(RemoteEntity, self).__init__(**kwargs)
        if not self.id:
            self.id = uuid.uuid4()
        if not self.data:
            self.data = {}

    def fetch_instance(self):
        return self.type.model.query.get(self.internal_id)
