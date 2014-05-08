from __future__ import absolute_import, division

import uuid

from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.schema import Index

from changes.config import db
from changes.db.types.guid import GUID


class FileCoverage(db.Model):
    __tablename__ = 'filecoverage'
    __table_args__ = (
        Index('idx_filecoverage_job_id', 'job_id'),
        Index('idx_filecoverage_project_id', 'project_id'),
    )

    id = Column(GUID, nullable=False, primary_key=True, default=uuid.uuid4)
    step_id = Column(GUID, ForeignKey('jobstep.id', ondelete="CASCADE"))
    job_id = Column(GUID, ForeignKey('job.id', ondelete="CASCADE"), nullable=False)
    project_id = Column(GUID, ForeignKey('project.id', ondelete="CASCADE"), nullable=False)
    filename = Column(String(256), nullable=False, primary_key=True)
    data = Column(Text)
    date_created = Column(DateTime, default=datetime.utcnow)

    step = relationship('JobStep')
    job = relationship('Job')
    project = relationship('Project')

    def __init__(self, **kwargs):
        super(FileCoverage, self).__init__(**kwargs)
        if not self.id:
            self.id = uuid.uuid4()
