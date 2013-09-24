import uuid

from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, String, ForeignKeyConstraint
from sqlalchemy.orm import relationship

from buildbox.constants import Status, Result
from buildbox.db.base import Base
from buildbox.db.types.enum import Enum
from buildbox.db.types.guid import GUID


class Build(Base):
    __tablename__ = 'build'
    __table_args__ = (
        ForeignKeyConstraint(
            ['repository_id', 'parent_revision_sha'],
            ['revision.repository_id', 'revision.sha']
        ),
    )

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    repository_id = Column(GUID, ForeignKey('repository.id'), nullable=False)
    project_id = Column(GUID, ForeignKey('project.id'), nullable=False)
    parent_revision_sha = Column(String(40), nullable=False)
    patch_id = Column(GUID, ForeignKey('patch.id'))
    label = Column(String(128), nullable=False)
    status = Column(Enum(Status), nullable=False, default=Status.unknown)
    result = Column(Enum(Result), nullable=False, default=Result.unknown)
    date_started = Column(DateTime)
    date_finished = Column(DateTime)
    date_created = Column(DateTime, default=datetime.utcnow)

    repository = relationship('Repository')
    project = relationship('Project')
    parent_revision = relationship('Revision', remote_side=[repository_id, parent_revision_sha])
    patch = relationship('Patch')

    def __init__(self, **kwargs):
        super(Build, self).__init__(**kwargs)
        if not self.id:
            self.id = uuid.uuid4()

    @property
    def duration(self):
        if self.date_started and self.date_finished:
            duration = self.date_finished - self.date_started
        else:
            duration = None
        return duration
