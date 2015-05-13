from sqlalchemy import Column, Integer

from changes.config import db
from changes.db.types.guid import GUID


class ItemSequence(db.Model):
    """
    Used to hold counters for autoincrement-style sequence number generation.
    In each row, value is the last sequence number returned for the
    corresponding parent.

    The table is used via the next_item_value database function and not used in
    the python codebase.
    """
    __tablename__ = 'itemsequence'

    parent_id = Column(GUID, nullable=False, primary_key=True)
    value = Column(Integer, default=0, server_default='0', nullable=False,
                   primary_key=True)
