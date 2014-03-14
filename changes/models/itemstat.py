from uuid import uuid4

from sqlalchemy import Column, String, Integer
from sqlalchemy.schema import UniqueConstraint

from changes.config import db
from changes.db.types.guid import GUID


class ItemStat(db.Model):
    __tablename__ = 'itemstat'
    __table_args__ = (
        UniqueConstraint('item_id', 'name', name='unq_itemstat_name'),
    )

    id = Column(GUID, primary_key=True, default=uuid4)
    item_id = Column(GUID, nullable=False)
    name = Column(String(64), nullable=False)
    value = Column(Integer, nullable=False)

    def __init__(self, **kwargs):
        super(ItemStat, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid4()
