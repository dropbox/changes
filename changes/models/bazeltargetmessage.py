import uuid

from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from changes.config import db
from changes.db.types.guid import GUID


class BazelTargetMessage(db.Model):
    """
    An optional message associated with a bazel target to display to the user.
    """

    __tablename__ = 'bazeltargetmessage'

    id = Column(GUID, nullable=False, primary_key=True, default=uuid.uuid4)
    target_id = Column(GUID, ForeignKey('bazeltarget.id', ondelete='CASCADE'), nullable=False)
    text = Column(Text, nullable=False)
    date_created = Column(DateTime, default=datetime.utcnow, nullable=False)

    target = relationship('BazelTarget', backref='messages')

    def __init__(self, **kwargs):
        super(BazelTargetMessage, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid.uuid4()
        if self.date_created is None:
            self.date_created = datetime.utcnow()
