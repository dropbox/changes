
from datetime import datetime
from hashlib import sha1
from sqlalchemy import (
    Column, DateTime, ForeignKey, String, Text
)
from sqlalchemy.orm import relationship, backref
from uuid import uuid4

from changes.config import db
from changes.db.types.guid import GUID


class Change(db.Model):
    """
    A change represents an independent change (eventually a single, finalized
    patch) and may contain many revisions of the same patch (which may be
    represented as many builds).

    Take for example a code review system like Phabricator. You submit a patch
    which is called a 'Revision', and inside of it there may be many 'diffs'. We
    attempt to represent the top level Revision as a singular Change.

    The primary component is the hash, which is determined by the backend and
    generally consists of something like SHA1(REVISION_ID).
    """
    __tablename__ = 'change'

    id = Column(GUID, primary_key=True, default=uuid4)
    hash = Column(String(40), unique=True, nullable=False)
    repository_id = Column(GUID, ForeignKey('repository.id', ondelete="CASCADE"), nullable=False)
    project_id = Column(GUID, ForeignKey('project.id', ondelete="CASCADE"), nullable=False)
    author_id = Column(GUID, ForeignKey('author.id', ondelete="CASCADE"))
    label = Column(String(128), nullable=False)
    message = Column(Text)
    date_created = Column(DateTime, default=datetime.utcnow)
    date_modified = Column(DateTime, default=datetime.utcnow)

    repository = relationship('Repository')
    project = relationship('Project', backref=backref('changes', order_by='Change.date_created'))
    author = relationship('Author')

    def __init__(self, **kwargs):
        super(Change, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid4()
        if self.hash is None:
            self.hash = sha1(uuid4().hex).hexdigest()
        if self.date_created is None:
            self.date_created = datetime.utcnow()
        if self.date_modified is None:
            self.date_modified = datetime.utcnow()
