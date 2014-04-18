from __future__ import absolute_import, division

import re
import uuid

from datetime import datetime
from hashlib import sha1
from sqlalchemy import Column, DateTime, ForeignKey, String, Text, Integer
from sqlalchemy.event import listen
from sqlalchemy.orm import deferred, relationship
from sqlalchemy.schema import UniqueConstraint, Index

from changes.config import db
from changes.constants import Result
from changes.db.types.enum import Enum
from changes.db.types.guid import GUID
from changes.db.utils import model_repr


class TestSuite(db.Model):
    """
    A test suite is usually representive of the tooling running the tests.

    Tests are unique per test suite.
    """
    __tablename__ = 'testsuite'
    __table_args__ = (
        UniqueConstraint('job_id', 'name_sha', name='_suite_key'),
        Index('idx_testsuite_project_id', 'project_id'),
    )

    id = Column(GUID, nullable=False, primary_key=True, default=uuid.uuid4)
    job_id = Column(GUID, ForeignKey('job.id', ondelete="CASCADE"), nullable=False)
    project_id = Column(GUID, ForeignKey('project.id', ondelete="CASCADE"), nullable=False)
    name_sha = Column(String(40), nullable=False, default=sha1('default').hexdigest())
    name = Column(Text, nullable=False, default='default')
    date_created = Column(DateTime, default=datetime.utcnow, nullable=False)

    job = relationship('Job')
    project = relationship('Project')

    __repr__ = model_repr('name')

    def __init__(self, **kwargs):
        super(TestSuite, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid.uuid4()
        if self.date_created is None:
            self.date_created = datetime.utcnow()
        if self.name is None:
            self.name = 'default'


class TestCase(db.Model):
    """
    An individual test result.
    """
    __tablename__ = 'test'
    __table_args__ = (
        UniqueConstraint('job_id', 'suite_id', 'label_sha', name='unq_test_key'),
        Index('idx_test_project_id', 'project_id'),
        Index('idx_test_suite_id', 'suite_id'),
        Index('idx_test_step_id', 'step_id'),
        Index('idx_test_project_key', 'project_id', 'label_sha'),
    )

    id = Column(GUID, nullable=False, primary_key=True, default=uuid.uuid4)
    job_id = Column(GUID, ForeignKey('job.id', ondelete="CASCADE"), nullable=False)
    project_id = Column(GUID, ForeignKey('project.id', ondelete="CASCADE"), nullable=False)
    step_id = Column(GUID, ForeignKey('jobstep.id', ondelete="CASCADE"))
    suite_id = Column(GUID, ForeignKey('testsuite.id', ondelete="CASCADE"))
    name_sha = Column('label_sha', String(40), nullable=False)
    name = Column(Text, nullable=False)
    _package = Column('package', Text, nullable=True)
    result = Column(Enum(Result), default=Result.unknown, nullable=False)
    duration = Column(Integer, default=0)
    message = deferred(Column(Text))
    date_created = Column(DateTime, default=datetime.utcnow, nullable=False)
    reruns = Column(Integer)

    job = relationship('Job')
    step = relationship('JobStep')
    project = relationship('Project')
    suite = relationship('TestSuite')

    __repr__ = model_repr('name', '_package', 'result')

    def __init__(self, **kwargs):
        super(TestCase, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid.uuid4()
        if self.result is None:
            self.result = Result.unknown
        if self.date_created is None:
            self.date_created = datetime.utcnow()

    @classmethod
    def calculate_name_sha(self, name):
        if name:
            return sha1(name).hexdigest()
        raise ValueError

    @property
    def sep(self):
        name = (self._package or self.name)
        # handle the case where it might begin with some special character
        if not re.match(r'^[a-zA-Z0-9]', name):
            return '/'
        elif '/' in name:
            return '/'
        return '.'

    def _get_package(self):
        if not self._package:
            try:
                package, _ = self.name.rsplit(self.sep, 1)
            except ValueError:
                package, _ = None, self.name
        else:
            package = self._package
        return package

    def _set_package(self, value):
        self._package = value

    package = property(_get_package, _set_package)

    @property
    def short_name(self):
        package = self.package
        if package and self.name.startswith(package):
            return self.name[len(package) + 1:]
        return self.name


def set_name_sha(target, value, oldvalue, initiator):
    if not value:
        return value

    new_sha = sha1(value).hexdigest()
    if new_sha != target.name_sha:
        target.name_sha = new_sha
    return value


listen(TestCase.name, 'set', set_name_sha, retval=False)
listen(TestSuite.name, 'set', set_name_sha, retval=False)
