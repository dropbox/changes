from uuid import uuid4

from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, String, Integer
from sqlalchemy.orm import relationship, backref
from sqlalchemy.schema import UniqueConstraint, CheckConstraint

from changes.config import db
from changes.db.types.guid import GUID
from changes.db.types.json import JSONEncodedDict
from changes.db.utils import model_repr
from changes.utils.imports import import_string


class Step(db.Model):
    """
    Represents one of N build steps for a plan.
    """
    # TODO(dcramer): only a single step is currently supported
    id = Column(GUID, primary_key=True, default=uuid4)
    plan_id = Column(GUID, ForeignKey('plan.id', ondelete='CASCADE'), nullable=False)
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
            self.id = uuid4()
        if self.date_created is None:
            self.date_created = datetime.utcnow()
        if self.date_modified is None:
            self.date_modified = self.date_created

    def get_implementation(self):
        try:
            cls = import_string(self.implementation)
        except Exception:
            return None

        return cls(**self.data)
