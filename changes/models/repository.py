import os.path
from uuid import uuid4

from datetime import datetime
from enum import Enum
from flask import current_app
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.schema import UniqueConstraint

from changes.config import db
from changes.db.types.enum import Enum as EnumType
from changes.db.types.guid import GUID


class RepositoryBackend(Enum):
    unknown = 0
    git = 1
    hg = 2

    def __str__(self):
        return BACKEND_LABELS[self]


class RepositoryStatus(Enum):
    inactive = 0
    active = 1
    importing = 2

    def __str__(self):
        return STATUS_LABELS[self]


BACKEND_LABELS = {
    RepositoryBackend.unknown: 'Unknown',
    RepositoryBackend.git: 'git',
    RepositoryBackend.hg: 'hg',
}

STATUS_LABELS = {
    RepositoryStatus.inactive: 'Inactive',
    RepositoryStatus.active: 'Active',
    RepositoryStatus.importing: 'importing',
}


class Repository(db.Model):
    __tablename__ = 'repository'

    id = Column(GUID, primary_key=True, default=uuid4)
    url = Column(String(200), nullable=False, unique=True)
    backend = Column(EnumType(RepositoryBackend),
                     default=RepositoryBackend.unknown, nullable=False)
    status = Column(EnumType(RepositoryStatus),
                    default=RepositoryStatus.inactive,
                    nullable=False, server_default='1')
    date_created = Column(DateTime, default=datetime.utcnow)

    last_update = Column(DateTime)
    last_update_attempt = Column(DateTime)

    def __init__(self, **kwargs):
        super(Repository, self).__init__(**kwargs)
        if not self.id:
            self.id = uuid4()
        if not self.date_created:
            self.date_created = datetime.utcnow()

    def get_vcs(self):
        from changes.vcs.git import GitVcs
        from changes.vcs.hg import MercurialVcs

        options = dict(
            db.session.query(
                RepositoryOption.name, RepositoryOption.value
            ).filter(
                RepositoryOption.repository_id == self.id,
                RepositoryOption.name.in_([
                    'auth.username',
                ])
            )
        )

        kwargs = {
            'path': os.path.join(current_app.config['REPO_ROOT'], self.id.hex),
            'url': self.url,
            'username': options.get('auth.username'),
        }

        if self.backend == RepositoryBackend.git:
            return GitVcs(**kwargs)
        elif self.backend == RepositoryBackend.hg:
            return MercurialVcs(**kwargs)
        else:
            return None

    @classmethod
    def get(cls, id):
        result = cls.query.filter_by(url=id).first()
        if result is None and len(id) == 32:
            result = cls.query.get(id)
        return result


class RepositoryOption(db.Model):
    __tablename__ = 'repositoryoption'
    __table_args__ = (
        UniqueConstraint('repository_id', 'name', name='unq_repositoryoption_name'),
    )

    id = Column(GUID, primary_key=True, default=uuid4)
    repository_id = Column(GUID, ForeignKey('repository.id'), nullable=False)
    name = Column(String(64), nullable=False)
    value = Column(Text, nullable=False)
    date_created = Column(DateTime, default=datetime.utcnow, nullable=False)

    repository = relationship('Repository')
