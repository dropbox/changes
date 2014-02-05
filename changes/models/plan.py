from uuid import uuid4

from datetime import datetime
from sqlalchemy import Column, DateTime, String
from sqlalchemy.ext.associationproxy import association_proxy

from changes.config import db
from changes.db.types.guid import GUID
from changes.db.types.json import JSONEncodedDict
from changes.db.utils import model_repr


class Plan(db.Model):
    """
    Represents one of N build plans for a project.
    """
    id = Column(GUID, primary_key=True, default=uuid4)
    label = Column(String(128), nullable=False)
    date_created = Column(DateTime, default=datetime.utcnow, nullable=False)
    date_modified = Column(DateTime, default=datetime.utcnow, nullable=False)
    data = Column(JSONEncodedDict)

    projects = association_proxy('plan_projects', 'project')

    __repr__ = model_repr('label')
    __tablename__ = 'plan'

    def __init__(self, **kwargs):
        super(Plan, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid4()
        if self.date_created is None:
            self.date_created = datetime.utcnow()
        if self.date_modified is None:
            self.date_modified = self.date_created
