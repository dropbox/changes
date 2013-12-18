import uuid

from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, String, Integer
from sqlalchemy.orm import relationship, backref
from sqlalchemy.schema import UniqueConstraint, CheckConstraint

from changes.config import db
from changes.db.types.guid import GUID
from changes.db.types.json import JSONEncodedDict
from changes.db.utils import model_repr
from changes.utils.imports import import_string


class Plan(db.Model):
    """
    Represents one of N build plans for a project.
    """
    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    label = Column(String(128), nullable=False)
    date_created = Column(DateTime, default=datetime.utcnow, nullable=False)
    date_modified = Column(DateTime, default=datetime.utcnow, nullable=False)
    data = Column(JSONEncodedDict)

    __repr__ = model_repr('label')
    __tablename__ = 'plan'

    def __init__(self, **kwargs):
        super(Plan, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid.uuid4()
        if self.date_created is None:
            self.date_created = datetime.utcnow()
        if self.date_modified is None:
            self.date_modified = self.date_created


class Step(db.Model):
    """
    Represents one of N build steps for a plan.
    """
    # TODO(dcramer): only a single step is currently supported
    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    plan_id = Column(GUID, ForeignKey('plan.id'), nullable=False)
    date_created = Column(DateTime, default=datetime.utcnow, nullable=False)
    date_modified = Column(DateTime, default=datetime.utcnow, nullable=False)
    # implementation should be class path notation
    implementation = Column(String(128), nullable=False)
    order = Column(Integer, nullable=False)
    data = Column(JSONEncodedDict)

    plan = relationship('Plan', backref=backref('steps', order_by='Step.order'))

    __repr__ = model_repr('plan_id', 'implementation')
    __tablename__ = 'step'
    __table_args__ = (
        UniqueConstraint('plan_id', 'order', name='unq_plan_key'),
        CheckConstraint(order >= 0, name='chk_step_order_positive'),
    )

    def __init__(self, **kwargs):
        super(Step, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid.uuid4()
        if self.date_created is None:
            self.date_created = datetime.utcnow()
        if self.date_modified is None:
            self.date_modified = self.date_created

    def get_implementation(self):
        return import_string(self.implementation)
