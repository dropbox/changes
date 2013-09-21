import uuid

from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text

from buildbox.db.base import Base
from buildbox.db.types.guid import GUID


class Revision(Base):
    __tablename__ = 'revision'

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    repository_id = Column(GUID, ForeignKey('repository.id'))
    author_id = Column(GUID, ForeignKey('author.id'))
    sha = Column(String(40), nullable=False)
    date_created = Column(DateTime, default=datetime.utcnow)
    message = Column(Text)
