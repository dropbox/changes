import uuid

from datetime import datetime
from sqlalchemy import Column, String, DateTime

from buildbox.db.base import Base
from buildbox.db.types.guid import GUID


class Author(Base):
    __tablename__ = 'author'

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    name = Column(String(128), nullable=False)
    email = Column(String(128))
    date_created = Column(DateTime, default=datetime.utcnow)
