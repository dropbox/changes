from __future__ import absolute_import, division

import uuid

from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.schema import UniqueConstraint, Index

from changes.config import db
from changes.db.types.guid import GUID


class AggregateTestSuite(db.Model):
    __tablename__ = 'aggtestsuite'
    __table_args__ = (
        UniqueConstraint('project_id', 'name_sha', name='unq_aggtestsuite_key'),
        Index('idx_aggtestsuite_first_build_id', 'first_build_id'),
    )

    id = Column(GUID, nullable=False, primary_key=True, default=uuid.uuid4)
    project_id = Column(GUID, ForeignKey('project.id'), nullable=False)
    name_sha = Column(String(40), nullable=False)
    name = Column(Text, nullable=False)
    first_build_id = Column(GUID, ForeignKey('build.id'), nullable=False)
    last_build_id = Column(GUID, ForeignKey('build.id'), nullable=False)
    date_created = Column(DateTime, default=datetime.utcnow, nullable=False)

    project = relationship('Project')
    first_build = relationship('Build', foreign_keys=[first_build_id])
    last_build = relationship('Build', foreign_keys=[last_build_id])

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
    project_id = Column(GUID, ForeignKey('project.id'), nullable=False)
    suite_id = Column(GUID, ForeignKey('aggtestsuite.id'))
    parent_id = Column(GUID, ForeignKey('aggtestgroup.id'))
    name_sha = Column(String(40), nullable=False)
    name = Column(Text, nullable=False)
    first_build_id = Column(GUID, ForeignKey('build.id'), nullable=False)
    last_build_id = Column(GUID, ForeignKey('build.id'), nullable=False)
    date_created = Column(DateTime, default=datetime.utcnow, nullable=False)

    project = relationship('Project')
    suite = relationship('AggregateTestSuite')
    parent = relationship('AggregateTestGroup', remote_side=[id])
    first_build = relationship('Build', foreign_keys=[first_build_id])
    last_build = relationship('Build', foreign_keys=[last_build_id])

    def __init__(self, **kwargs):
        super(AggregateTestGroup, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid.uuid4()
        if self.date_created is None:
            self.date_created = datetime.utcnow()
