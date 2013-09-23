import uuid

from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from buildbox.db.base import Base
from buildbox.db.types.guid import GUID


class Project(Base):
    __tablename__ = 'project'

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    slug = Column(String(64), unique=True, nullable=False)
    repository_id = Column(GUID, ForeignKey('repository.id'), nullable=False)
    name = Column(String(64))
    date_created = Column(DateTime, default=datetime.utcnow)

    repository = relationship('Repository', backref='projects')

    def __init__(self, **kwargs):
        super(Project, self).__init__(**kwargs)
        if not self.id:
            self.id = uuid.uuid4()
