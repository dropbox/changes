from datetime import datetime
from sqlalchemy import Column, String, DateTime

from buildbox.db.base import Base
from buildbox.db.types.guid import GUID


class Author(Base):
    __tablename__ = 'author'

    author_id = Column(GUID, primary_key=True)
    name = Column(String(128), nullable=False)
    email = Column(String(128))
    date_created = Column(DateTime, default=datetime.utcnow)
