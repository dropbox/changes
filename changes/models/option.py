from uuid import uuid4

from typing import Dict, List

from collections import defaultdict
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


class ItemOptionsHelper(object):
    @staticmethod
    def get_options(item_id_list, options_list):
        options_query = db.session.query(
            ItemOption.item_id, ItemOption.name, ItemOption.value
        ).filter(
            ItemOption.item_id.in_(item_id_list),
            ItemOption.name.in_(options_list)
        )

        options = defaultdict(dict)
        for item_id, option_name, option_value in options_query:
            options[item_id][option_name] = option_value

        return options
