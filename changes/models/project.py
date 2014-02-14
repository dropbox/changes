from datetime import datetime
from slugify import slugify
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Text
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import backref, relationship, joinedload
from sqlalchemy.schema import UniqueConstraint
from uuid import uuid4

from changes.config import db
from changes.db.types.guid import GUID


class Project(db.Model):
    __tablename__ = 'project'

    id = Column(GUID, primary_key=True, default=uuid4)
    slug = Column(String(64), unique=True, nullable=False)
    repository_id = Column(GUID, ForeignKey('repository.id', ondelete="RESTRICT"), nullable=False)
    name = Column(String(64))
    date_created = Column(DateTime, default=datetime.utcnow)
    avg_build_time = Column(Integer)

    repository = relationship('Repository')
    plans = association_proxy('project_plans', 'plan')

    def __init__(self, **kwargs):
        super(Project, self).__init__(**kwargs)
        if not self.id:
            self.id = uuid4()
        if not self.slug:
            self.slug = slugify(self.name)

    @classmethod
    def get(cls, id):
        project = cls.query.options(
            joinedload(cls.repository, innerjoin=True),
        ).filter_by(slug=id).first()
        if project is None and len(id) == 32:
            project = cls.query.options(
                joinedload(cls.repository),
            ).get(id)
        return project


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


class ProjectPlan(db.Model):
    __tablename__ = 'project_plan'

    project_id = Column(GUID, ForeignKey('project.id', ondelete="CASCADE"),
                        nullable=False, primary_key=True)
    plan_id = Column(GUID, ForeignKey('plan.id', ondelete="CASCADE"),
                     nullable=False, primary_key=True)
    avg_build_time = Column(Integer)

    project = relationship('Project', backref=backref(
        "project_plans", cascade="all, delete-orphan"))
    plan = relationship('Plan', backref=backref(
        "plan_projects", cascade="all, delete-orphan"))

    def __init__(self, project=None, plan=None, **kwargs):
        kwargs.setdefault('project', project)
        kwargs.setdefault('plan', plan)
        super(ProjectPlan, self).__init__(**kwargs)
