from datetime import datetime
from slugify import slugify
from sqlalchemy import (
    Table, Column, String, DateTime, ForeignKey, Integer, Text
)
from sqlalchemy.orm import relationship
from sqlalchemy.schema import UniqueConstraint
from uuid import uuid4

from changes.config import db
from changes.db.types.guid import GUID


project_plan_m2m_table = Table(
    'project_plan',
    db.Model.metadata,
    Column('project_id', GUID, ForeignKey('project.id'), nullable=False, primary_key=True),
    Column('plan_id', GUID, ForeignKey('plan.id'), nullable=False, primary_key=True)
)


class Project(db.Model):
    __tablename__ = 'project'

    id = Column(GUID, primary_key=True, default=uuid4)
    slug = Column(String(64), unique=True, nullable=False)
    repository_id = Column(GUID, ForeignKey('repository.id', ondelete="RESTRICT"), nullable=False)
    name = Column(String(64))
    date_created = Column(DateTime, default=datetime.utcnow)
    avg_build_time = Column(Integer)

    repository = relationship('Repository')
    plans = relationship('Plan', secondary=project_plan_m2m_table, backref="projects")

    def __init__(self, **kwargs):
        super(Project, self).__init__(**kwargs)
        if not self.id:
            self.id = uuid4()
        if not self.slug:
            self.slug = slugify(self.name)

    def get_entity(self, provider):
        if not hasattr(self, '_entities') or provider not in self._entities:
            raise ValueError('Entity not attached')
        return self._entities[provider]

    def attach_entity(self, entity):
        assert entity.internal_id == self.id

        if not hasattr(self, '_entities'):
            self._entities = {}
        self._entities[entity.provider] = entity


class ProjectOption(db.Model):
    __tablename__ = 'projectoption'
    __table_args__ = (
        UniqueConstraint('project_id', 'name', name='unq_projectoption_name'),
    )

    id = Column(GUID, primary_key=True, default=uuid4)
    project_id = Column(GUID, ForeignKey('project.id', ondelete="CASCADE"), nullable=False)
    name = Column(String(64), nullable=False)
    value = Column(Text, nullable=False)
    date_created = Column(DateTime, default=datetime.utcnow, nullable=False)

    project = relationship('Project')

    def __init__(self, **kwargs):
        super(ProjectOption, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid4()
        if self.date_created is None:
            self.date_created = datetime.utcnow()
