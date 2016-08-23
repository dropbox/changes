import uuid

from datetime import datetime
from sqlalchemy import Boolean, Column, String, DateTime
from sqlalchemy.dialects.postgresql import ARRAY

from changes.config import db
from changes.db.types.guid import GUID


class User(db.Model):
    """
    A table of the people who use changes.
    """
    __tablename__ = 'user'

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    email = Column(String(128), unique=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    date_created = Column(DateTime, default=datetime.utcnow)

    # this keeps track of the list of wildcard patterns of project names that
    # the user has access to. For example:
    # - `foo` matches `foo`
    # - `foo.*` matches anything starting with `foo.`, like `foo.staging`, `foo.`
    # - `*foo*` matches anything containing `foo`, like `barfoobar`, `foo`
    project_permissions = Column(ARRAY(String(256)), nullable=True)

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if not self.id:
            self.id = uuid.uuid4()
        if not self.date_created:
            self.date_created = datetime.utcnow()
