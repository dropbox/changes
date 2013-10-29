from __future__ import absolute_import, division

import uuid

from datetime import datetime
from hashlib import sha1
from sqlalchemy import Column, DateTime, ForeignKey, String, Text, Integer
from sqlalchemy.event import listen
from sqlalchemy.orm import relationship
from sqlalchemy.schema import UniqueConstraint

from changes.config import db
from changes.constants import Result
from changes.db.types.enum import Enum
from changes.db.types.guid import GUID


class Test(db.Model):
    __tablename__ = 'test'
    __table_args__ = (
        UniqueConstraint('build_id', 'group_sha', 'label_sha', name='_test_key'),
    )

    id = Column(GUID, nullable=False, primary_key=True, default=uuid.uuid4)
    build_id = Column(GUID, ForeignKey('build.id'), nullable=False)
    project_id = Column(GUID, ForeignKey('project.id'), nullable=False)
    group_sha = Column(String(40), nullable=False, default=sha1('default').hexdigest())
    label_sha = Column(String(40), nullable=False)
    group = Column(Text, nullable=False, default='default')
    name = Column(Text, nullable=False)
    package = Column(Text, nullable=True)
    result = Column(Enum(Result))
    duration = Column(Integer)
    message = Column(Text)
    date_created = Column(DateTime, default=datetime.utcnow)

    build = relationship('Build')
    project = relationship('Project')

    def __init__(self, **kwargs):
        super(Test, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid.uuid4()
        if self.result is None:
            self.result = Result.unknown
        if self.date_created is None:
            self.date_created = datetime.utcnow()

    def calculate_label_sha(self):
        if self.package and self.name:
            return sha1('{0}.{1}'.format(self.package, self.name)).hexdigest()
        elif self.name:
            return sha1(self.name).hexdigest()

    def calculate_group_sha(self):
        return sha1(self.group or 'default').hexdigest()


def set_label_sha(target, value, oldvalue, initiator):
    target.label_sha = target.calculate_label_sha()
    return value


def set_group_sha(target, value, oldvalue, initiator):
    target.group_sha = target.calculate_group_sha()
    return value


listen(Test.package, 'set', set_label_sha, retval=False)
listen(Test.name, 'set', set_label_sha, retval=False)
listen(Test.group, 'set', set_group_sha, retval=False)
