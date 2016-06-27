import uuid

from sqlalchemy import Column, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship
from sqlalchemy.schema import Index

from changes.config import db
from changes.db.types.guid import GUID


class TestMessage(db.Model):
    """
    The message produced by a run of a test.

    This is generally captured from standard output/error by the test machine, and is extracted from the junit.xml file.
    We record it as a byte offset in the junit.xml artifact entry.
    """

    __tablename__ = 'testmessage'
    __table_args__ = (
        Index('idx_testmessage_test_id', 'test_id'),
    )

    id = Column(GUID, nullable=False, primary_key=True, default=uuid.uuid4)
    test_id = Column(GUID, ForeignKey('test.id', ondelete="CASCADE"), nullable=False)
    artifact_id = Column(GUID, ForeignKey('artifact.id', ondelete="CASCADE"), nullable=False)
    label = Column(Text, nullable=False)
    start_offset = Column(Integer, default=0, nullable=False)
    length = Column(Integer, nullable=False)

    test = relationship('TestCase', backref='messages')
    artifact = relationship('Artifact')

    def __init__(self, **kwargs):
        super(TestMessage, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid.uuid4()

    def get_message(self):
        return self.artifact.file.get_file(self.start_offset, self.length).read()
