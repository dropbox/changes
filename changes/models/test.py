from __future__ import absolute_import, division

import uuid

from datetime import datetime
from hashlib import sha1
from sqlalchemy import Table, Column, DateTime, ForeignKey, String, Text, Integer
from sqlalchemy.event import listen
from sqlalchemy.orm import relationship
from sqlalchemy.schema import UniqueConstraint, Index

from changes.config import db
from changes.constants import Result
from changes.db.types.enum import Enum
from changes.db.types.guid import GUID
from changes.db.types.json import JSONEncodedDict


test_group_m2m_table = Table(
    'testgroup_test',
    db.Model.metadata,
    Column('group_id', GUID, ForeignKey('testgroup.id'), nullable=False, primary_key=True),
    Column('test_id', GUID, ForeignKey('test.id'), nullable=False, primary_key=True)
)


class TestSuite(db.Model):
    """
    A test suite is usually representive of the tooling running the tests.

    Tests are unique per test suite.
    """
    __tablename__ = 'testsuite'
    __table_args__ = (
        UniqueConstraint('build_id', 'name_sha', name='_suite_key'),
        Index('idx_project_id', 'project_id'),
    )

    id = Column(GUID, nullable=False, primary_key=True, default=uuid.uuid4)
    build_id = Column(GUID, ForeignKey('build.id'), nullable=False)
    project_id = Column(GUID, ForeignKey('project.id'), nullable=False)
    name_sha = Column(String(40), nullable=False, default=sha1('default').hexdigest())
    name = Column(Text, nullable=True, default='default')
    date_created = Column(DateTime, default=datetime.utcnow)

    build = relationship('Build')
    project = relationship('Project')

    def __init__(self, **kwargs):
        super(TestSuite, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid.uuid4()
        if self.date_created is None:
            self.date_created = datetime.utcnow()
        if self.name is None:
            self.name = 'default'

    def calculate_name_sha(self):
        return sha1(self.name or 'default').hexdigest()


class TestGroup(db.Model):
    """
    A TestGroup represents an aggregate tree of all leaves under it.

    e.g. if you have the test leaf "foo.bar.TestCase.test_foo" it might create
    a tree for "foo.bar.TestCase", "foo.bar" and "foo".
    """
    __tablename__ = 'testgroup'
    __table_args__ = (
        UniqueConstraint('build_id', 'suite_id', 'name_sha', name='_group_key'),
        Index('idx_project_id', 'project_id'),
        Index('idx_suite_id', 'suite_id'),
        Index('idx_parent_id', 'parent_id'),
    )

    id = Column(GUID, nullable=False, primary_key=True, default=uuid.uuid4)
    build_id = Column(GUID, ForeignKey('build.id'), nullable=False)
    project_id = Column(GUID, ForeignKey('project.id'), nullable=False)
    suite_id = Column(GUID, ForeignKey('testsuite.id'))
    parent_id = Column(GUID, ForeignKey('testgroup.id'))
    name_sha = Column(String(40), nullable=False)
    name = Column(Text)
    duration = Column(Integer, default=0)
    num_tests = Column(Integer, default=0)
    num_failed = Column(Integer, default=0)
    data = Column(JSONEncodedDict)
    date_created = Column(DateTime, default=datetime.utcnow)

    build = relationship('Build')
    project = relationship('Project')
    testcases = relationship('TestCase', secondary=test_group_m2m_table, backref="groups")

    def __init__(self, **kwargs):
        super(TestGroup, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid.uuid4()
        if self.date_created is None:
            self.date_created = datetime.utcnow()
        if self.duration is None:
            self.duration = 0
        if self.num_tests is None:
            self.num_tests = 0
        print self.name, self.name_sha

    def calculate_name_sha(self):
        if not self.name:
            return
        return sha1(self.name).hexdigest()


class TestCase(db.Model):
    """
    An individual test result.
    """
    __tablename__ = 'test'
    __table_args__ = (
        UniqueConstraint('build_id', 'suite_id', 'label_sha', name='unq_test_key'),
        Index('idx_test_project_id', 'project_id'),
        Index('idx_test_suite_id', 'suite_id'),
    )

    id = Column(GUID, nullable=False, primary_key=True, default=uuid.uuid4)
    build_id = Column(GUID, ForeignKey('build.id'), nullable=False)
    project_id = Column(GUID, ForeignKey('project.id'), nullable=False)
    suite_id = Column(GUID, ForeignKey('testsuite.id'))
    name_sha = Column('label_sha', String(40), nullable=False)
    name = Column(Text, nullable=False)
    package = Column(Text, nullable=True)
    result = Column(Enum(Result))
    duration = Column(Integer)
    message = Column(Text)
    date_created = Column(DateTime, default=datetime.utcnow)

    build = relationship('Build')
    project = relationship('Project')

    def __init__(self, **kwargs):
        super(TestCase, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid.uuid4()
        if self.result is None:
            self.result = Result.unknown
        if self.date_created is None:
            self.date_created = datetime.utcnow()


def test_name_sha_func(attr):
    def set_name_sha(target, value, oldvalue, initiator):
        if attr == 'package':
            package = value
        else:
            package = target.package
        if attr == 'name':
            name = value
        else:
            name = target.name

        if package and name:
            new_sha = sha1('{0}.{1}'.format(package, name)).hexdigest()
        elif name:
            new_sha = sha1(name).hexdigest()

        if new_sha != target.name_sha:
            target.name_sha = new_sha
        return value
    return set_name_sha


def set_name_sha(target, value, oldvalue, initiator):
    if not value:
        return value

    new_sha = sha1(value).hexdigest()
    if new_sha != target.name_sha:
        target.name_sha = new_sha
    return value


listen(TestCase.package, 'set', test_name_sha_func('package'), retval=False)
listen(TestCase.name, 'set', test_name_sha_func('name'), retval=False)
listen(TestSuite.name, 'set', set_name_sha, retval=False)
listen(TestGroup.name, 'set', set_name_sha, retval=False)
