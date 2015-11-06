from __future__ import absolute_import

import uuid

from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship, backref
from sqlalchemy.schema import UniqueConstraint

from changes.config import db
from changes.db.types.filestorage import FileData, FileStorage
from changes.db.types.guid import GUID
from changes.db.types.json import JSONEncodedDict

ARTIFACT_STORAGE_OPTIONS = {
    'path': 'artifacts',
}


class Artifact(db.Model):
    """
    The artifact produced by one job/step, produced on a single machine.
    Sometimes this is a JSON dict referencing a file in S3, sometimes
    it is Null, sometimes it is an empty dict. It is basically any file
    left behind after a run for changes to pick up
    """
    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    job_id = Column(GUID, ForeignKey('job.id', ondelete="CASCADE"), nullable=False)
    step_id = Column(GUID, ForeignKey('jobstep.id', ondelete="CASCADE"), nullable=False)
    project_id = Column(GUID, ForeignKey('project.id', ondelete="CASCADE"), nullable=False)
    name = Column(String(1024), nullable=False)
    date_created = Column(DateTime, nullable=False, default=datetime.utcnow)
    data = Column(JSONEncodedDict)
    file = Column(FileStorage(**ARTIFACT_STORAGE_OPTIONS))

    job = relationship('Job', backref=backref('artifacts'))
    project = relationship('Project')
    step = relationship('JobStep', backref=backref('artifacts'))

    __tablename__ = 'artifact'
    __table_args__ = (
        UniqueConstraint('step_id', 'name', name='unq_artifact_name'),
    )

    def __init__(self, **kwargs):
        super(Artifact, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid.uuid4()
        if self.date_created is None:
            self.date_created = datetime.utcnow()
        if self.data is None:
            self.data = {}
        if self.file is None:
            # TODO(dcramer): this is super hacky but not sure a better way to
            # do it with SQLAlchemy
            self.file = FileData({}, ARTIFACT_STORAGE_OPTIONS)
