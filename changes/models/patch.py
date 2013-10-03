from uuid import uuid4

from datetime import datetime
from sqlalchemy import (
    Column, DateTime, ForeignKey, String, Text
)
from sqlalchemy.orm import relationship

from changes.config import db
from changes.db.types.guid import GUID


class Patch(db.Model):
    __tablename__ = 'patch'

    id = Column(GUID, primary_key=True, default=uuid4)
    change_id = Column(GUID, ForeignKey('change.id'))
    repository_id = Column(GUID, ForeignKey('repository.id'), nullable=False)
    project_id = Column(GUID, ForeignKey('project.id'), nullable=False)
    parent_revision_sha = Column(String(40), nullable=False)
    label = Column(String(64), nullable=False)
    url = Column(String(200))
    diff = Column(Text)
    message = Column(Text)
    date_created = Column(DateTime, default=datetime.utcnow)

    change = relationship('Change')
    repository = relationship('Repository')
    project = relationship('Project')

    def __init__(self, **kwargs):
        super(Patch, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid4()
        if self.date_created is None:
            self.date_created = datetime.utcnow()
