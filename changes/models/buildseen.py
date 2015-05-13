from __future__ import absolute_import

import uuid

from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.schema import UniqueConstraint

from changes.config import db
from changes.db.types.guid import GUID
from changes.db.utils import model_repr


class BuildSeen(db.Model):
    """
    Keeps track of when users have viewed builds in the ui.
    Not sure we expose this to users in the ui right now.
    """
    __tablename__ = 'buildseen'
    __table_args__ = (
        UniqueConstraint('build_id', 'user_id', name='unq_buildseen_entity'),
    )

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    build_id = Column(GUID, ForeignKey('build.id', ondelete="CASCADE"), nullable=False)
    user_id = Column(GUID, ForeignKey('user.id', ondelete="CASCADE"), nullable=False)
    date_created = Column(DateTime, default=datetime.utcnow, nullable=False)

    build = relationship('Build')
    user = relationship('User')

    __repr__ = model_repr('build_id', 'user_id')

    def __init__(self, **kwargs):
        super(BuildSeen, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid.uuid4()
        if self.date_created is None:
            self.date_created = datetime.utcnow()
