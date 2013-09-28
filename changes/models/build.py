import uuid

from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship

from changes.config import db
from changes.constants import Status, Result
from changes.db.types.enum import Enum
from changes.db.types.guid import GUID


class Build(db.Model):
    __tablename__ = 'build'

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    change_id = Column(GUID, ForeignKey('change.id'))
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

    change = relationship('Change')
    repository = relationship('Repository')
    project = relationship('Project')
    patch = relationship('Patch')
    author = relationship('Author')

    def __init__(self, **kwargs):
        super(Build, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid.uuid4()
        if self.result is None:
            self.result = Result.unknown
        if self.status is None:
            self.status = Result.unknown
        if self.date_created is None:
            self.date_created = datetime.utcnow()

    @property
    def duration(self):
        """
        Return the duration (in milliseconds) that this item was in-progress.
        """
        if self.date_started and self.date_finished:
            duration = (self.date_finished - self.date_started).total_seconds() * 1000
        else:
            duration = None
        return duration

    @property
    def progress(self):
        if self.status == Status.finished:
            return 100
        elif self.status != Status.in_progress:
            return 0

        # avg_build_time = self.project.avg_build_time

        # # TODO: we need a state for this
        # if not avg_build_time:
        avg_build_time = 600

        seconds_elapsed = (datetime.utcnow() - self.date_started).total_seconds()

        percent = int(seconds_elapsed / max(avg_build_time, seconds_elapsed + 60) * 100)

        return min(max(percent, 1), 99)
