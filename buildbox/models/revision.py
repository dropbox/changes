from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey

from buildbox.db.base import Base
from buildbox.db.types.guid import GUID


class Revision(Base):
    __tablename__ = 'revision'

    repository_id = Column(GUID, ForeignKey('repository.repository_id'), primary_key=True)
    revision_id = Column(GUID, primary_key=True)
    author_id = Column(GUID, ForeignKey('author.author_id'))
    sha = Column(String(40), nullable=False)
    date_created = Column(DateTime, default=datetime.utcnow)
