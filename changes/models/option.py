from uuid import uuid4

from datetime import datetime
from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.schema import UniqueConstraint

from changes.config import db
from changes.db.types.guid import GUID


class ItemOption(db.Model):
    __tablename__ = 'itemoption'
    __table_args__ = (
        UniqueConstraint('item_id', 'name', name='unq_itemoption_name'),
    )

    id = Column(GUID, primary_key=True, default=uuid4)
    item_id = Column(GUID, nullable=False)
    name = Column(String(64), nullable=False)
    value = Column(Text, nullable=False)
    date_created = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __init__(self, **kwargs):
        super(ItemOption, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid4()
        if self.date_created is None:
            self.date_created = datetime.utcnow()
