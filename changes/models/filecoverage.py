from __future__ import absolute_import, division

import uuid

from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, String, Text, Integer
# from sqlalchemy.orm import relationship

from changes.config import db
from changes.db.types.guid import GUID


class FileCoverage(db.Model):
    __tablename__ = 'filecoverage'

    id = Column(GUID, nullable=False, primary_key=True, default=uuid.uuid4)
    build_id = Column(GUID, ForeignKey('build.id'), nullable=False)
    project_id = Column(GUID, ForeignKey('project.id'), nullable=False)
    filename = Column(String(256), nullable=False, primary_key=True)
    project_id = Column(Integer, nullable=False)
    data = Column(Text)
    date_created = Column(DateTime, default=datetime.utcnow)

    # build = relationship('Build')
    # project = relationship('Project')

    def __init__(self, **kwargs):
        super(FileCoverage, self).__init__(**kwargs)
        if not self.id:
            self.id = uuid.uuid4()
