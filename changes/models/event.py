from __future__ import absolute_import

import uuid

from datetime import datetime
from sqlalchemy import Column, DateTime, String
from sqlalchemy.schema import Index, UniqueConstraint

from changes.config import db
from changes.db.types.guid import GUID
from changes.db.types.json import JSONEncodedDict
from changes.db.utils import model_repr


class EventType(object):
    email = 'email_notification'
    hipchat = 'hipchat_notification'
    green_build = 'green_build_notification'


class Event(db.Model):
    __tablename__ = 'event'
    __table_args__ = (
        Index('idx_event_item_id', 'item_id'),
        # Having this as unique prevents duplicate events, but in the future
        # we may want to allow duplicates
        # e.g. we can have a "sent email notification" event, but maybe
        # we'd want to have multiple of those
        UniqueConstraint('type', 'item_id', name='unq_event_key'),
    )

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    type = Column(String(32), nullable=False)
    item_id = Column('item_id', GUID, nullable=False)
    date_created = Column(DateTime, default=datetime.utcnow)
    date_modified = Column(DateTime, default=datetime.utcnow)
    data = Column(JSONEncodedDict)

    __repr__ = model_repr('type', 'item_id')

    def __init__(self, **kwargs):
        super(Event, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid.uuid4()
        if self.date_created is None:
            self.date_created = datetime.utcnow()
        if self.date_modified is None:
            self.date_modified = self.date_created
