import uuid

from datetime import datetime
from sqlalchemy import (
    Column, DateTime, ForeignKey, String, LargeBinary, ForeignKeyConstraint
)
from sqlalchemy.orm import relationship

from buildbox.config import db
from buildbox.db.types.guid import GUID


class Patch(db.Model):
    __tablename__ = 'patch'
    __table_args__ = (
        ForeignKeyConstraint(
            ['repository_id', 'parent_revision_sha'],
            ['revision.repository_id', 'revision.sha']
        ),
    )

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    change_id = Column(GUID, ForeignKey('change.id'))
    repository_id = Column(GUID, ForeignKey('repository.id'), nullable=False)
    project_id = Column(GUID, ForeignKey('project.id'), nullable=False)
    parent_revision_sha = Column(String(40), nullable=False)
    label = Column(String(64), nullable=False)
    url = Column(String(200), nullable=False)
    diff = Column(LargeBinary)
    date_created = Column(DateTime, default=datetime.utcnow)

    change = relationship('Change')
    repository = relationship('Repository')
    project = relationship('Project')
    parent_revision = relationship('Revision')
