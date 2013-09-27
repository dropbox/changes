import uuid

from datetime import datetime
from sqlalchemy import (
    Column, DateTime, ForeignKey, String, ForeignKeyConstraint
)
from sqlalchemy.orm import relationship, backref

from changes.config import db
from changes.db.types.guid import GUID


class Change(db.Model):
    """
    A change represents an independent change (eventually a single, finalized
    patch) and may contain many revisions of the same patch (which may be
    represented as many builds).

    Take for example a code review system like Phabricator. You submit a patch
    which is called a 'Revision', and inside of it there may be many 'diffs'. We
    attempt to represent the top level Revision as a singular Change.

    The primary component is the hash, which is determined by the backend and
    generally consists of something like SHA1(REVISION_ID).
    """
    __tablename__ = 'change'
    __table_args__ = (
        ForeignKeyConstraint(
            ['repository_id', 'parent_revision_sha'],
            ['revision.repository_id', 'revision.sha']
        ),
        ForeignKeyConstraint(
            ['repository_id', 'revision_sha'],
            ['revision.repository_id', 'revision.sha']
        ),
    )

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    hash = Column(String(40), unique=True, nullable=False)
    repository_id = Column(GUID, ForeignKey('repository.id'), nullable=False)
    project_id = Column(GUID, ForeignKey('project.id'), nullable=False)
    revision_sha = Column(String(40))
    parent_revision_sha = Column(String(40))
    author_id = Column(GUID, ForeignKey('author.id'))
    label = Column(String(128), nullable=False)
    date_created = Column(DateTime, default=datetime.utcnow)
    date_finished = Column(DateTime)

    repository = relationship('Repository')
    project = relationship('Project', backref=backref('changes', order_by='Change.date_created'))
    # parent_revision = relationship('Revision', foreign_keys=[repository_id, parent_revision_sha])
    # revision = relationship('Revision', foreign_keys=[repository_id, revision_sha])
    author = relationship('Author')

    def __init__(self, **kwargs):
        super(Change, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid.uuid4()
        if self.date_created is None:
            self.date_created = datetime.utcnow()

    def to_dict(self):
        return {
            'id': self.id.hex,
            'hash': self.group_key,
            'name': self.label,
            'project': self.project.to_dict(),
            'author': self.author.to_dict() if self.author else None,
            'parent_revision': self.parent_revision.to_dict(),
            'duration': self.duration,
            'link': '/projects/%s/builds/%s/' % (self.project.slug, self.id.hex),
            'dateCreated': self.date_created.isoformat(),
            'dateFinished': self.date_finished.isoformat() if self.date_finished else None,
        }
