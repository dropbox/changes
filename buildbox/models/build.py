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
    parent_revision_sha = Column(String(40))
    patch_id = Column(GUID, ForeignKey('patch.id'))
    author_id = Column(GUID, ForeignKey('author.id'))
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
    author = relationship('Author')

    def __init__(self, **kwargs):
        super(Build, self).__init__(**kwargs)
        if not self.id:
            self.id = uuid.uuid4()

    @property
    def duration(self):
        if self.date_started and self.date_finished:
            duration = (self.date_finished - self.date_started).total_seconds()
        else:
            duration = None
        return duration

    def to_dict(self):
        from buildbox.app import application

        return {
            'id': self.id.hex,
            'name': self.label,
            'result': self.result.to_dict(),
            'status': self.status.to_dict(),
            'project': self.project.to_dict(),
            'author': self.author.to_dict(),
            'duration': self.duration,
            'link': application.reverse_url('build-details', self.project.slug, self.id.hex),
            'dateCreated': self.date_created.isoformat(),
            'dateStarted': self.date_started.isoformat() if self.date_started else None,
            'dateFinished': self.date_finished.isoformat() if self.date_finished else None,
        }
