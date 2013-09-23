import uuid

from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from buildbox.constants import Status, Result
from buildbox.db.base import Base
from buildbox.db.types.enum import Enum
from buildbox.db.types.guid import GUID


class Step(Base):
    __tablename__ = 'step'

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    build_id = Column(GUID, ForeignKey('build.id'), nullable=False)
    phase_id = Column(GUID, ForeignKey('phase.id'), nullable=False)
    repository_id = Column(GUID, ForeignKey('repository.id'), nullable=False)
    project_id = Column(String(64), ForeignKey('project.id'), nullable=False)
    label = Column(String(128), nullable=False)
    status = Column(Enum(Status), nullable=False, default=0)
    result = Column(Enum(Result), nullable=False, default=0)
    node_id = Column(GUID, ForeignKey('node.id'))
    date_started = Column(DateTime)
    date_finished = Column(DateTime)
    date_created = Column(DateTime, default=datetime.utcnow)

    build = relationship('Build')
    project = relationship('Project')
    repository = relationship('Repository')
    phase = relationship('Phase', backref='steps')

    @property
    def duration(self):
        if self.date_started and self.date_finished:
            duration = self.date_finished - self.date_started
        else:
            duration = None
        return duration
