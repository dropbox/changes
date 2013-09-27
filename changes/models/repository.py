import uuid

from datetime import datetime
from sqlalchemy import Column, String, DateTime

from changes.config import db
from changes.db.types.guid import GUID


class Repository(db.Model):
    __tablename__ = 'repository'

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    url = Column(String(200), nullable=False, unique=True)
    date_created = Column(DateTime, default=datetime.utcnow)

    def __init__(self, **kwargs):
        super(Repository, self).__init__(**kwargs)
        if not self.id:
            self.id = uuid.uuid4()
