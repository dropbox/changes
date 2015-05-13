from __future__ import absolute_import

import uuid
from sqlalchemy import UniqueConstraint, Column, ForeignKey, String
from sqlalchemy.orm import relationship
from changes.config import db
from changes.db.types.guid import GUID


class LatestGreenBuild(db.Model):
    """
    Represents the latest green build for a given branch of a given project

    A project with multiple latest_green_builds is because it has multiple branches
    """
    __tablename__ = 'latest_green_build'
    __table_args__ = (
        UniqueConstraint('project_id', 'branch', name='unq_project_branch'),
    )

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    project_id = Column(GUID, ForeignKey('project.id'), nullable=False)
    build_id = Column(GUID, ForeignKey('build.id'), nullable=False)
    branch = Column(String(128))

    project = relationship('Project', innerjoin=True)
    build = relationship('Build', innerjoin=True)

    def __init__(self, **kwargs):
        super(LatestGreenBuild, self).__init__(**kwargs)
        if not self.id:
            self.id = uuid.uuid4()
