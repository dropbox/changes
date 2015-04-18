from uuid import uuid4, UUID

from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from changes.config import db
from changes.db.types.guid import GUID


class AdminMessage(db.Model):
    """ A system-level message that should be displayed to users.

    This can be used to hold information about outages, upcoming down-time or
    new features. These messages are intended to be set only by admins, but
    displayed to all users of the system.
    """
    __tablename__ = 'adminmessage'

    id = Column(GUID, primary_key=True, default=uuid4)
    user_id = Column(GUID, ForeignKey('user.id', ondelete="CASCADE"), nullable=False)
    message = Column(Text)
    date_created = Column(DateTime, default=datetime.utcnow)

    user = relationship('User', foreign_keys=[user_id], innerjoin=False)

    def __init__(self, **kwargs):
        super(AdminMessage, self).__init__(**kwargs)
        # For now, we only allow a single entry in the notification DB
        if self.id is None:
            self.id = UUID('a35ed88b-3cb7-4905-b7b8-177eb55c027c')
        if self.date_created is None:
            self.date_created = datetime.utcnow()
