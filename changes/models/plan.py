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
    What work should we do for our new revision? A project may have multiple
    plans, e.g. whenever a diff comes in, test it on both mac and windows
    (each being its own plan.) In theory, a plan consists of a sequence of
    steps; in practice, a plan is just a wrapper around a single step.
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
    # If not None, use snapshot from another plan. This allows us to share
    # a single snapshot between multiple plans.
    #
    # This plan must be a plan from the same project (or else jobstep_details
    # will fail) but this is not enforced by the database schema because we do
    # not use a composite key.
    snapshot_plan_id = Column(GUID, ForeignKey('plan.id', ondelete="SET NULL"), nullable=True)
    avg_build_time = Column(Integer)

    project = relationship('Project', backref=backref('plans'))
    snapshot_plan = relationship('Plan', remote_side=[id])

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

    def get_item_options(self):
        from changes.models import ItemOption
        options_query = db.session.query(
            ItemOption.name, ItemOption.value
        ).filter(
            ItemOption.item_id == self.id,
        )
        options = dict()
        for opt_name, opt_value in options_query:
            options[opt_name] = opt_value
        return options
