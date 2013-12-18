import uuid

from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, String, Text, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.schema import Index

from changes.config import db
from changes.constants import Status, Result, Cause
from changes.db.types.enum import Enum
from changes.db.types.guid import GUID
from changes.db.types.json import JSONEncodedDict
from changes.db.utils import model_repr


class Build(db.Model):
    __tablename__ = 'build'
    __table_args__ = (
        Index('idx_build_project_id', 'project_id'),
        Index('idx_build_repository_id', 'repository_id'),
        Index('idx_build_author_id', 'author_id'),
        Index('idx_build_patch_id', 'patch_id'),
        Index('idx_build_change_id', 'change_id'),
        Index('idx_build_source_id', 'source_id'),
    )

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    # TODO(dcramer): change should be removed in favor of an m2m between
    # Change and Source
    change_id = Column(GUID, ForeignKey('change.id'))
    project_id = Column(GUID, ForeignKey('project.id'), nullable=False)
    source_id = Column(GUID, ForeignKey('source.id'))
    # TODO(dcramer): repo/sha/patch_id should be removed in favor of source
    repository_id = Column(GUID, ForeignKey('repository.id'), nullable=False)
    revision_sha = Column(String(40))
    patch_id = Column(GUID, ForeignKey('patch.id'))
    parent_id = Column(GUID, ForeignKey('build.id'))
    label = Column(String(128), nullable=False)
    status = Column(Enum(Status), nullable=False, default=Status.unknown)
    result = Column(Enum(Result), nullable=False, default=Result.unknown)
    # TODO(dcramer): message, target, cause, and author should be removed in
    # favor of reading them from BuildFamily
    message = Column(Text)
    target = Column(String(128))
    cause = Column(Enum(Cause), nullable=False, default=Cause.unknown)
    author_id = Column(GUID, ForeignKey('author.id'))
    duration = Column(Integer)
    date_started = Column(DateTime)
    date_finished = Column(DateTime)
    date_created = Column(DateTime, default=datetime.utcnow)
    date_modified = Column(DateTime, default=datetime.utcnow)
    data = Column(JSONEncodedDict)

    change = relationship('Change')
    repository = relationship('Repository')
    project = relationship('Project')
    source = relationship('Source')
    patch = relationship('Patch')
    author = relationship('Author')
    parent = relationship('Build')

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
        if self.date_started and self.date_finished and not self.duration:
            self.duration = (self.date_finished - self.date_started).total_seconds() * 1000
