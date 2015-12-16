from __future__ import absolute_import

import uuid

from datetime import datetime
from enum import Enum
from sqlalchemy import Column, DateTime, ForeignKey, String, Text, Integer
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.schema import Index, UniqueConstraint
from sqlalchemy.sql import func, select

from changes.config import db
from changes.constants import Status, Result, Cause
from changes.db.types.enum import Enum as EnumType
from changes.db.types.guid import GUID
from changes.db.types.json import JSONEncodedDict
from changes.db.utils import model_repr


class BuildPriority(Enum):
    default = 0
    high = 100
    low = -100


class Build(db.Model):
    """
    Represents the work we do (e.g. running tests) for one diff or commit (an
    entry in the source table) in one particular project

    Each Build contains many Jobs (usually linked to a JobPlan).
    """
    __tablename__ = 'build'
    __table_args__ = (
        Index('idx_buildfamily_project_id', 'project_id'),
        Index('idx_buildfamily_author_id', 'author_id'),
        Index('idx_buildfamily_source_id', 'source_id'),
        UniqueConstraint('project_id', 'number', name='unq_build_number'),
    )

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    number = Column(Integer)
    project_id = Column(GUID, ForeignKey('project.id', ondelete="CASCADE"), nullable=False)
    # A unqiue identifier for a group of related Builds, such as all Builds created by a particular
    # action. Used primarily for aggregation in result reporting.
    # Note that this may be None for Builds that aren't grouped, and all such Builds should NOT
    # be treated as a collection.
    collection_id = Column(GUID)
    source_id = Column(GUID, ForeignKey('source.id', ondelete="CASCADE"))
    author_id = Column(GUID, ForeignKey('author.id', ondelete="CASCADE"))
    cause = Column(EnumType(Cause), nullable=False, default=Cause.unknown)
    # label is a short description, typically from the title of the change that triggered the build.
    label = Column(String(128), nullable=False)
    # short indicator of what is being built, typically the sha or the Phabricator revision ID like 'D90885'.
    target = Column(String(128))
    tags = Column(ARRAY(String(16)), nullable=True)
    status = Column(EnumType(Status), nullable=False, default=Status.unknown)
    result = Column(EnumType(Result), nullable=False, default=Result.unknown)
    message = Column(Text)
    duration = Column(Integer)
    priority = Column(EnumType(BuildPriority), nullable=False,
                      default=BuildPriority.default, server_default='0')
    date_started = Column(DateTime)
    date_finished = Column(DateTime)
    date_decided = Column(DateTime)  # date when final determination of build result is made
    date_created = Column(DateTime, default=datetime.utcnow)
    date_modified = Column(DateTime, default=datetime.utcnow)
    data = Column(JSONEncodedDict)

    project = relationship('Project', innerjoin=True)
    source = relationship('Source', innerjoin=True)
    author = relationship('Author')
    stats = relationship('ItemStat',
                         primaryjoin='Build.id == ItemStat.item_id',
                         foreign_keys=[id],
                         uselist=True)

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
        if self.tags is None:
            self.tags = []
