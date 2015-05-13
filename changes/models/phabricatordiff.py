from __future__ import absolute_import

from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from uuid import uuid4

from changes.config import db
from changes.db.types.guid import GUID


class PhabricatorDiff(db.Model):
    """
    Whenever phabricator sends us a diff to do a build against (see source/patch
    for more info), we write an entry to this table with the details.
    revision_id and diff_id refer to the phabricator versions of this
    terminology: revision_id is the number in D145201 and diff_id represents
    a particular diff within that differential revision (the id in the
    revision update history table.)

    This is 80% convenient logging. It also does light deduplication: we make
    sure to never kick off more than one build for a particular
    revision_id/diff_id from the api called by phabricator. Phabricator can
    occasionally fire a herald rule more than once, so its nice to have this.

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
