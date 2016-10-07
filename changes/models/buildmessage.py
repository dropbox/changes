import uuid

from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from changes.config import db
from changes.db.types.guid import GUID


class BuildMessage(db.Model):
    """
    An optional message associated with a build to display to the user.

    This is only for UI purposes - there is no impact on the build result.
    """

    __tablename__ = 'buildmessage'

    id = Column(GUID, nullable=False, primary_key=True, default=uuid.uuid4)
    build_id = Column(GUID, ForeignKey('build.id', ondelete='CASCADE'), nullable=False)
    text = Column(Text, nullable=False)
    date_created = Column(DateTime, default=datetime.utcnow, nullable=False)

    build = relationship('Build', backref='messages')

    def __init__(self, **kwargs):
        super(BuildMessage, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid.uuid4()
        if self.date_created is None:
            self.date_created = datetime.utcnow()
