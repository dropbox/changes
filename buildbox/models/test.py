from __future__ import absolute_import, division

import uuid

from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, String, Text, Integer
from sqlalchemy.orm import relationship

from buildbox.constants import Result
from buildbox.db.base import Base
from buildbox.db.types.enum import Enum
from buildbox.db.types.guid import GUID


class Test(Base):
    __tablename__ = 'test'

    id = Column(GUID, nullable=False, primary_key=True, default=uuid.uuid4)
    build_id = Column(GUID, ForeignKey('build.id'), nullable=False)
    project_id = Column(GUID, ForeignKey('project.id'), nullable=False)
    label = Column(String(256), nullable=False, primary_key=True)
    result = Column(Enum(Result))
    duration = Column(Integer)
    message = Column(Text)
    date_created = Column(DateTime, default=datetime.utcnow)

    build = relationship('Build')
    project = relationship('Project')

    def __init__(self, **kwargs):
        super(Test, self).__init__(**kwargs)
        if not self.id:
            self.id = uuid.uuid4()

    def to_dict(self):
        return {
            'id': self.id.hex,
            'name': self.label,
            'result': self.result.to_dict(),
            'duration': self.duration,
            'dateCreated': self.date_created.isoformat(),
            'message': self.message,
        }
