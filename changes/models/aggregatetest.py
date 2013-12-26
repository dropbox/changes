from __future__ import absolute_import, division

import uuid

from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.schema import UniqueConstraint, Index

from changes.config import db
from changes.db.types.guid import GUID
from changes.db.utils import model_repr


class AggregateTestSuite(db.Model):
    __tablename__ = 'aggtestsuite'
    __table_args__ = (
        UniqueConstraint('project_id', 'name_sha', name='unq_aggtestsuite_key'),
        Index('idx_aggtestsuite_first_build_id', 'first_build_id'),
    )

    id = Column(GUID, nullable=False, primary_key=True, default=uuid.uuid4)
    project_id = Column(GUID, ForeignKey('project.id', ondelete="CASCADE"), nullable=False)
    name_sha = Column(String(40), nullable=False)
    name = Column(Text, nullable=False)
    first_build_id = Column(GUID, ForeignKey('job.id', ondelete="CASCADE"), nullable=False)
    last_build_id = Column(GUID, ForeignKey('job.id', ondelete="CASCADE"), nullable=False)
    date_created = Column(DateTime, default=datetime.utcnow, nullable=False)

    project = relationship('Project')
    first_build = relationship('Job', foreign_keys=[first_build_id])
    last_build = relationship('Job', foreign_keys=[last_build_id])

    __repr__ = model_repr('name')

    def __init__(self, **kwargs):
        super(AggregateTestSuite, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid.uuid4()
        if self.date_created is None:
            self.date_created = datetime.utcnow()
        if self.name is None:
            self.name = 'default'


class AggregateTestGroup(db.Model):
    __tablename__ = 'aggtestgroup'
    __table_args__ = (
        UniqueConstraint('project_id', 'suite_id', 'name_sha', name='unq_aggtestgroup_key'),
        Index('idx_aggtestgroup_suite_id', 'suite_id'),
        Index('idx_aggtestgroup_parent_id', 'parent_id'),
        Index('idx_aggtestgroup_first_build_id', 'first_build_id'),
    )
    id = Column(GUID, nullable=False, primary_key=True, default=uuid.uuid4)
    project_id = Column(GUID, ForeignKey('project.id', ondelete="CASCADE"), nullable=False)
    suite_id = Column(GUID, ForeignKey('aggtestsuite.id', ondelete="CASCADE"))
    parent_id = Column(GUID, ForeignKey('aggtestgroup.id', ondelete="CASCADE"))
    name_sha = Column(String(40), nullable=False)
    name = Column(Text, nullable=False)
    first_build_id = Column(GUID, ForeignKey('job.id', ondelete="CASCADE"), nullable=False)
    last_build_id = Column(GUID, ForeignKey('job.id', ondelete="CASCADE"), nullable=False)
    date_created = Column(DateTime, default=datetime.utcnow, nullable=False)

    project = relationship('Project')
    suite = relationship('AggregateTestSuite')
    parent = relationship('AggregateTestGroup', remote_side=[id])
    first_build = relationship('Job', foreign_keys=[first_build_id])
    last_build = relationship('Job', foreign_keys=[last_build_id])

    # last_testgroup = relationship(
    #     'TestGroup', primaryjoin="and_(AggregateTestGroup.name_sha==TestGroup.name_sha, "
    #     "AggregateTestGroup.last_build_id==TestGroup.build_id)")

    __repr__ = model_repr('name')

    def __init__(self, **kwargs):
        super(AggregateTestGroup, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid.uuid4()
        if self.date_created is None:
            self.date_created = datetime.utcnow()
