from __future__ import absolute_import, division

import uuid

from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.orm import relationship
from sqlalchemy.schema import UniqueConstraint

from changes.config import db
from changes.constants import Result
from changes.db.types.enum import Enum
from changes.db.types.guid import GUID


class RevisionResult(db.Model):
    __tablename__ = 'revisionresult'
    __table_args__ = (
        UniqueConstraint('project_id', 'revision_sha', name='unq_project_revision_pair'),
    )

    id = Column(GUID, nullable=False, primary_key=True, default=uuid.uuid4)
    build_id = Column(GUID, ForeignKey('build.id'))
    revision_sha = Column(String(40), nullable=False)
    project_id = Column(GUID, ForeignKey('project.id', ondelete='CASCADE'), nullable=False)
    result = Column(Enum(Result), nullable=False, default=Result.unknown)

    build = relationship('Build')
    project = relationship('Project')

    def __init__(self, **kwargs):
        super(RevisionResult, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid.uuid4()
        if self.result is None:
            self.result = Result.unknown
