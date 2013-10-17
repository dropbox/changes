import uuid

from datetime import datetime
from sqlalchemy import Column, DateTime, String, UniqueConstraint

from changes.config import db
from changes.db.types.guid import GUID
from changes.db.types.json import JSONEncodedDict


class RemoteEntity(db.Model):
    __tablename__ = 'remoteentity'
    __table_args__ = (
        UniqueConstraint('provider', 'remote_id', 'type', name='remote_identifier'),
    )

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    type = Column(String, nullable=False)
    provider = Column(String(128), nullable=False)
    remote_id = Column(String(128), nullable=False)
    internal_id = Column(GUID, nullable=False)
    data = Column(JSONEncodedDict, default=dict)
    date_created = Column(DateTime, default=datetime.utcnow)

    def __init__(self, **kwargs):
        super(RemoteEntity, self).__init__(**kwargs)
        if not self.id:
            self.id = uuid.uuid4()
        if not self.data:
            self.data = {}

    def fetch_instance(self):
        return self.type.model.query.get(self.internal_id)
