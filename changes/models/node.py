import uuid

from datetime import datetime
from sqlalchemy import Column, DateTime, String

from changes.config import db
from changes.db.types.guid import GUID


class Node(db.Model):
    __tablename__ = 'node'

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    label = Column(String(128))
    date_created = Column(DateTime, default=datetime.utcnow)

    def __init__(self, **kwargs):
        super(Node, self).__init__(**kwargs)
        if not self.id:
            self.id = uuid.uuid4()
