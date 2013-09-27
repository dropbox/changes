from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from changes.config import db
from changes.db.types.guid import GUID


class Revision(db.Model):
    __tablename__ = 'revision'

    repository_id = Column(GUID, ForeignKey('repository.id'), primary_key=True)
    sha = Column(String(40), primary_key=True)
    author_id = Column(GUID, ForeignKey('author.id'))
    message = Column(Text)
    date_created = Column(DateTime, default=datetime.utcnow)

    repository = relationship('Repository')
    author = relationship('Author')

    def __init__(self, **kwargs):
        super(Revision, self).__init__(**kwargs)
        if self.date_created is None:
            self.date_created = datetime.utcnow()

    def to_dict(self):
        return {
            'sha': self.sha,
            'shaShort': self.sha[:12],
            'message': self.message,
            'author': self.author.to_dict() if self.author else None,
            'dateCreated': self.date_created.isoformat(),
        }
