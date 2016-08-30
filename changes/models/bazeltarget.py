from __future__ import absolute_import, division

import uuid

from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Text, Integer
from sqlalchemy.orm import backref, relationship

from changes.config import db
from changes.constants import Result, Status
from changes.db.types.enum import Enum
from changes.db.types.guid import GUID


class BazelTarget(db.Model):
    __tablename__ = 'bazeltarget'
    id = Column(GUID, nullable=False, primary_key=True, default=uuid.uuid4)
    step_id = Column(GUID, ForeignKey('jobstep.id', ondelete="CASCADE"), nullable=False)
    job_id = Column(GUID, ForeignKey('job.id', ondelete="CASCADE"), nullable=False)
    name = Column(Text, nullable=False)
    status = Column(Enum(Status), nullable=False, default=Status.unknown)
    result = Column(Enum(Result), default=Result.unknown, nullable=False)
    duration = Column(Integer, default=0)
    date_created = Column(DateTime, default=datetime.utcnow, nullable=False)

    tests = relationship('TestCase', backref=backref('target'))

    def __init__(self, **kwargs):
        super(BazelTarget, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid.uuid4()
        if self.result is None:
            self.result = Result.unknown
        if self.status is None:
            self.status = Status.unknown
        if self.date_created is None:
            self.date_created = datetime.utcnow()
