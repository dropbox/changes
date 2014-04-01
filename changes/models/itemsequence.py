from sqlalchemy import Column, Integer

from changes.config import db
from changes.db.types.guid import GUID


class ItemSequence(db.Model):
    __tablename__ = 'itemsequence'

    parent_id = Column(GUID, nullable=False, primary_key=True)
    value = Column(Integer, default=0, server_default='0', nullable=False,
                   primary_key=True)
