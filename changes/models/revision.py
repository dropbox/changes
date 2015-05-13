from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship

from changes.config import db
from changes.db.types.guid import GUID


class Revision(db.Model):
    """
    Represents a commit in a repository, including some metadata. Author and
    committer are stored as references to the author table. Ideally there
    will be one revision row for every commit in every repository tracked by
    changes, though this is not always true, and some code tries to degrade
    gracefully when this happens.

    Revisions are keyed by repository, sha. They do not have unique UUIDs
    """
    __tablename__ = 'revision'

    repository_id = Column(GUID, ForeignKey('repository.id'), primary_key=True)
    sha = Column(String(40), primary_key=True)
    author_id = Column(GUID, ForeignKey('author.id'))
    committer_id = Column(GUID, ForeignKey('author.id'))
    message = Column(Text)
    parents = Column(ARRAY(String(40)))
    branches = Column(ARRAY(String(128)))
    date_created = Column(DateTime, default=datetime.utcnow)
    date_committed = Column(DateTime, default=datetime.utcnow)

    repository = relationship('Repository')
    author = relationship('Author', foreign_keys=[author_id], innerjoin=False)
    committer = relationship('Author', foreign_keys=[committer_id], innerjoin=False)

    def __init__(self, **kwargs):
        super(Revision, self).__init__(**kwargs)
        if self.date_created is None:
            self.date_created = datetime.utcnow()
        if self.date_committed is None:
            self.date_committed = self.date_created

    @property
    def subject(self):
        return self.message.splitlines()[0]
