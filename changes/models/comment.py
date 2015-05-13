from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from uuid import uuid4

from changes.config import db
from changes.db.types.guid import GUID


class Comment(db.Model):
    __tablename__ = 'comment'

    id = Column(GUID, primary_key=True, default=uuid4)
    build_id = Column(GUID, ForeignKey('build.id', ondelete="CASCADE"), nullable=False)
    user_id = Column(GUID, ForeignKey('user.id', ondelete="CASCADE"), nullable=False)
    job_id = Column(GUID, ForeignKey('job.id', ondelete="CASCADE"))
    text = Column(Text)
    date_created = Column(DateTime, default=datetime.utcnow)

    build = relationship('Build')
    user = relationship('User')
    job = relationship('Job')

    def __init__(self, **kwargs):
        super(Comment, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid4()
        if self.date_created is None:
            self.date_created = datetime.utcnow()
