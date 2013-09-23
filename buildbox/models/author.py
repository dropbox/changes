import uuid

from datetime import datetime
from sqlalchemy import Column, String, DateTime

from buildbox.db.base import Base
from buildbox.db.types.guid import GUID


class Author(Base):
    __tablename__ = 'author'

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    name = Column(String(128), nullable=False, unique=True)
    email = Column(String(128), unique=True)
    date_created = Column(DateTime, default=datetime.utcnow)

    def __init__(self, **kwargs):
        super(Author, self).__init__(**kwargs)
        if not self.id:
            self.id = uuid.uuid4()
