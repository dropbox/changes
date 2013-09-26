from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from buildbox.config import db
from buildbox.db.types.guid import GUID


class Revision(db.Model):
    __tablename__ = 'revision'

    repository_id = Column(GUID, ForeignKey('repository.id'), primary_key=True)
    sha = Column(String(40), primary_key=True)
    author_id = Column(GUID, ForeignKey('author.id'))
    message = Column(Text)
    date_created = Column(DateTime, default=datetime.utcnow)

    repository = relationship('Repository')
    author = relationship('Author')

    def to_dict(self):
        return {
            'sha': self.sha,
            'shaShort': self.sha[:12],
            'message': self.message,
            'author': self.author.to_dict() if self.author else None,
            'dateCreated': self.date_created.isoformat(),
        }
