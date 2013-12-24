from __future__ import absolute_import

import uuid

from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.schema import Index

from changes.config import db
from changes.db.types.guid import GUID
from changes.db.utils import model_repr


class BuildPlan(db.Model):
    """
    A link to all Build + Plan's for a BuildFamily.

    TODO(dcramer): this should include a snapshot of the plan at build time.
    """
    __tablename__ = 'buildplan'
    __table_args__ = (
        Index('idx_buildplan_project_id', 'project_id'),
        Index('idx_buildplan_family_id', 'family_id'),
        Index('idx_buildplan_plan_id', 'plan_id'),
    )

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    project_id = Column(GUID, ForeignKey('project.id', ondelete="CASCADE"), nullable=False)
    family_id = Column(GUID, ForeignKey('buildfamily.id', ondelete="CASCADE"), nullable=False)
    build_id = Column(GUID, ForeignKey('build.id', ondelete="CASCADE"), nullable=False, unique=True)
    plan_id = Column(GUID, ForeignKey('plan.id', ondelete="CASCADE"), nullable=False)
    date_created = Column(DateTime, default=datetime.utcnow)
    date_modified = Column(DateTime, default=datetime.utcnow)

    project = relationship('Project')
    family = relationship('BuildFamily')
    build = relationship('Build')
    plan = relationship('Plan')

    __repr__ = model_repr('family_id', 'build_id', 'plan_id')

    def __init__(self, **kwargs):
        super(BuildPlan, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid.uuid4()
        if self.date_created is None:
            self.date_created = datetime.utcnow()
        if self.date_modified is None:
            self.date_modified = self.date_created
