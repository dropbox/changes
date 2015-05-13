from uuid import uuid4

from datetime import datetime
from enum import Enum
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import backref, relationship

from changes.config import db
from changes.db.types.enum import Enum as EnumType
from changes.db.types.guid import GUID
from changes.db.types.json import JSONEncodedDict
from changes.db.utils import model_repr


class PlanStatus(Enum):
    inactive = 0
    active = 1

    def __str__(self):
        return STATUS_LABELS[self]


STATUS_LABELS = {
    PlanStatus.inactive: 'Inactive',
    PlanStatus.active: 'Active',
}


class Plan(db.Model):
    """
    Represents one of N build plans for a project.
    """
    id = Column(GUID, primary_key=True, default=uuid4)
    project_id = Column(GUID, ForeignKey('project.id', ondelete="CASCADE"), nullable=False)
    label = Column(String(128), nullable=False)
    date_created = Column(DateTime, default=datetime.utcnow, nullable=False)
    date_modified = Column(DateTime, default=datetime.utcnow, nullable=False)
    data = Column(JSONEncodedDict)
    status = Column(EnumType(PlanStatus),
                    default=PlanStatus.inactive,
                    nullable=False, server_default='1')
    avg_build_time = Column(Integer)

    project = relationship('Project', backref=backref('plans'))

    __repr__ = model_repr('label')
    __tablename__ = 'plan'

    def __init__(self, **kwargs):
        super(Plan, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid4()
        if self.date_created is None:
            self.date_created = datetime.utcnow()
        if self.date_modified is None:
            self.date_modified = self.date_created
