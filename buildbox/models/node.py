import uuid

from datetime import datetime
from sqlalchemy import Column, DateTime, String

from buildbox.db.base import Base
from buildbox.db.types.guid import GUID


class Node(Base):
    __tablename__ = 'node'

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    label = Column(String(128))
    date_created = Column(DateTime, default=datetime.utcnow)
