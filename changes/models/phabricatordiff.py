from __future__ import absolute_import

from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from uuid import uuid4

from changes.config import db
from changes.db.types.guid import GUID


class PhabricatorDiff(db.Model):
    """
    A source represents the canonical parameters that a build is running against.

    It always implies a revision to build off (though until we have full repo
    integration this is considered optional, and defaults to tip/master), and
    an optional patch_id to apply on top of it.
    """
    id = Column(GUID, primary_key=True, default=uuid4)
    diff_id = Column(Integer, unique=True)
    revision_id = Column(Integer)
    source_id = Column(GUID, ForeignKey('source.id'))
    url = Column(String)
    date_created = Column(DateTime, default=datetime.utcnow)

    source = relationship('Source')

    __tablename__ = 'phabricatordiff'

    def __init__(self, **kwargs):
        super(PhabricatorDiff, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid4()
        if self.date_created is None:
            self.date_created = datetime.utcnow()
