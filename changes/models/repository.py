import os.path
import uuid

from datetime import datetime
from enum import Enum
from flask import current_app
from sqlalchemy import Column, String, DateTime

from changes.config import db
from changes.db.types.enum import Enum as EnumType
from changes.db.types.guid import GUID


class RepositoryBackend(Enum):
    unknown = 0
    git = 1
    hg = 2


class Repository(db.Model):
    __tablename__ = 'repository'

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    url = Column(String(200), nullable=False, unique=True)
    backend = Column(EnumType(RepositoryBackend),
                     default=RepositoryBackend.unknown, nullable=False)
    date_created = Column(DateTime, default=datetime.utcnow)

    last_update = Column(DateTime)
    last_update_attempt = Column(DateTime)

    def __init__(self, **kwargs):
        super(Repository, self).__init__(**kwargs)
        if not self.id:
            self.id = uuid.uuid4()
        if not self.date_created:
            self.date_created = datetime.utcnow()

    def get_vcs(self):
        from changes.vcs.git import GitVcs
        from changes.vcs.hg import MercurialVcs

        kwargs = {
            'path': os.path.join(current_app.config['REPO_ROOT'], self.id.hex),
            'url': self.url,
        }

        if self.backend == RepositoryBackend.git:
            return GitVcs(**kwargs)
        elif self.backend == RepositoryBackend.hg:
            return MercurialVcs(**kwargs)
        else:
            return None
