
from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship
from sqlalchemy.schema import UniqueConstraint, ForeignKeyConstraint
from uuid import uuid4

from changes.config import db
from changes.db.types.guid import GUID
from changes.db.types.json import JSONEncodedDict


class Source(db.Model):
    """
    This is the object that actually represents the code we run builds against.

    Essentially its a revision, with a UUID, and a possible patch_id. Rows
    with null patch_ids are just revisions, and rows with patch_ids apply
    the linked patch on top of the revision and run builds against the
    resulting code.

    Why the indirection? This is how we handle phabricator diffs: when we
    want to create a build for a new diff, we add a row here with the diff's
    parent revision sha (NOT the sha of the commit phabricator is trying to
    land, since that will change every time we update the diff) and a row
    to the patch table that contains the contents of the diff.

    Side note: Whenever we create a source row from a phabricator diff, we
    log json text to the data field with information like the diff id.

    """
    id = Column(GUID, primary_key=True, default=uuid4)
    repository_id = Column(GUID, ForeignKey('repository.id'), nullable=False)
    patch_id = Column(GUID, ForeignKey('patch.id'), unique=True)
    revision_sha = Column(String(40))
    date_created = Column(DateTime, default=datetime.utcnow)
    data = Column(JSONEncodedDict)

    repository = relationship('Repository', innerjoin=False)
    patch = relationship('Patch')
    revision = relationship('Revision',
                            foreign_keys=[repository_id, revision_sha])

    __tablename__ = 'source'
    __table_args__ = (
        ForeignKeyConstraint(
            ('repository_id', 'revision_sha'),
            ('revision.repository_id', 'revision.sha')
        ),
        UniqueConstraint(
            'repository_id', 'revision_sha', 'patch_id', name='unq_source_revision',
        ),
    )

    def __init__(self, **kwargs):
        super(Source, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid4()
        if self.date_created is None:
            self.date_created = datetime.utcnow()

    def generate_diff(self):
        diff = None

        if self.patch:
            diff = self.patch.diff
        else:
            vcs = self.repository.get_vcs()
            if vcs:
                try:
                    diff = vcs.export(self.revision_sha)
                except Exception:
                    pass

        if isinstance(diff, bytes):
            diff = diff.decode('utf-8')

        return diff

    def is_commit(self):
        return bool(self.patch_id is None and self.revision_sha)
