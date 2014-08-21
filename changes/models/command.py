import uuid

from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship, backref
from sqlalchemy.schema import UniqueConstraint

from changes.config import db
from changes.constants import Status
from changes.db.types.enum import Enum as EnumType
from changes.db.types.guid import GUID
from changes.db.types.json import JSONEncodedDict


class CommandType(Enum):
    default = 0
    collect_steps = 1
    collect_tests = 2
    setup = 3


class FutureCommand(object):
    def __init__(self, script, path=None, artifacts=None, env=None, label=None,
                 type=CommandType.default):
        if not label:
            label = script.splitlines()[0][:128]

        self.script = script
        self.path = path or ''
        self.artifacts = artifacts or []
        self.env = env or {}
        self.label = label
        self.type = type

    def as_command(self, jobstep, order):
        return Command(
            jobstep_id=jobstep.id,
            script=self.script,
            cwd=self.path,
            artifacts=self.artifacts,
            env=self.env,
            label=self.label,
            order=order,
            status=Status.queued,
            type=self.type,
        )


class Command(db.Model):
    __tablename__ = 'command'
    __table_args__ = (
        UniqueConstraint('jobstep_id', 'order', name='unq_command_order'),
    )

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    jobstep_id = Column(GUID, ForeignKey('jobstep.id', ondelete="CASCADE"), nullable=False)
    label = Column(String(128), nullable=False)
    status = Column(EnumType(Status), nullable=False, default=Status.unknown)
    return_code = Column(Integer, nullable=True)
    script = Column(Text(), nullable=False)
    env = Column(JSONEncodedDict, nullable=True)
    cwd = Column(String(256), nullable=True)
    artifacts = Column(ARRAY(String(256)), nullable=True)
    date_started = Column(DateTime)
    date_finished = Column(DateTime)
    date_created = Column(DateTime, default=datetime.utcnow)
    data = Column(JSONEncodedDict)
    order = Column(Integer, default=0, server_default='0', nullable=False)
    type = Column(EnumType(CommandType), nullable=False, default=CommandType.default,
                  server_default='0')

    jobstep = relationship('JobStep', backref=backref('commands', order_by='Command.order'))

    def __init__(self, **kwargs):
        super(Command, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid.uuid4()
        if self.status is None:
            self.status = Status.unknown
        if self.date_created is None:
            self.date_created = datetime.utcnow()
        if self.data is None:
            self.data = {}

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
