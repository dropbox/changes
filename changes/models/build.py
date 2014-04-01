from __future__ import absolute_import

import uuid

from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, String, Text, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.schema import Index, UniqueConstraint
from sqlalchemy.sql import func, select

from changes.config import db
from changes.constants import Status, Result, Cause
from changes.db.types.enum import Enum
from changes.db.types.guid import GUID
from changes.db.types.json import JSONEncodedDict
from changes.db.utils import model_repr


class Build(db.Model):
    """
    Represents a collection of builds for a single target, as well as the sum
    of their results.

    Each Build contains many Jobs (usually linked to a JobPlan).
    """
    __tablename__ = 'build'
    __table_args__ = (
        Index('idx_buildfamily_project_id', 'project_id'),
        Index('idx_buildfamily_repository_sha', 'repository_id', 'revision_sha'),
        Index('idx_buildfamily_author_id', 'author_id'),
        Index('idx_buildfamily_patch_id', 'patch_id'),
        Index('idx_buildfamily_source_id', 'source_id'),
        UniqueConstraint('project_id', 'number', name='unq_build_number'),
    )

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    number = Column(Integer)
    project_id = Column(GUID, ForeignKey('project.id', ondelete="CASCADE"), nullable=False)
    source_id = Column(GUID, ForeignKey('source.id', ondelete="CASCADE"))
    # TODO(dcramer): repo/sha/patch_id should be removed in favor of source
    revision_sha = Column(String(40))
    repository_id = Column(GUID, ForeignKey('repository.id', ondelete="CASCADE"), nullable=False)
    patch_id = Column(GUID, ForeignKey('patch.id', ondelete="CASCADE"))
    author_id = Column(GUID, ForeignKey('author.id', ondelete="CASCADE"))
    cause = Column(Enum(Cause), nullable=False, default=Cause.unknown)
    label = Column(String(128), nullable=False)
    target = Column(String(128))
    status = Column(Enum(Status), nullable=False, default=Status.unknown)
    result = Column(Enum(Result), nullable=False, default=Result.unknown)
    message = Column(Text)
    duration = Column(Integer)
    date_started = Column(DateTime)
    date_finished = Column(DateTime)
    date_created = Column(DateTime, default=datetime.utcnow)
    date_modified = Column(DateTime, default=datetime.utcnow)
    data = Column(JSONEncodedDict)

    project = relationship('Project', innerjoin=True)
    repository = relationship('Repository')
    source = relationship('Source', innerjoin=True)
    patch = relationship('Patch')
    author = relationship('Author')

    __repr__ = model_repr('label', 'target')

    def __init__(self, **kwargs):
        super(Build, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid.uuid4()
        if self.result is None:
            self.result = Result.unknown
        if self.status is None:
            self.status = Status.unknown
        if self.date_created is None:
            self.date_created = datetime.utcnow()
        if self.date_modified is None:
            self.date_modified = self.date_created
        if self.date_started and self.date_finished and not self.duration:
            self.duration = (self.date_finished - self.date_started).total_seconds() * 1000
        if self.number is None and self.project:
            self.number = select([func.next_item_value(self.project.id.hex)])
