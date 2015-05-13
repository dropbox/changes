from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from uuid import uuid4

from changes.config import db
from changes.db.types.guid import GUID


class Comment(db.Model):
    """
    Comments on test runs in changes. You can go into the GUI and leave
    messages, and this table keeps track of those. There is a job_id but it is
    always null, despite the UI showing you the comment only on the job page.

    Due to this, the UI will show an identical set of comments on every job
    page of a build.
    """
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
