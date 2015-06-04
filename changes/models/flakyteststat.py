from uuid import uuid4

from sqlalchemy import Column, Date, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship
from sqlalchemy.schema import Index, UniqueConstraint
import datetime

from changes.config import db
from changes.db.types.guid import GUID


class FlakyTestStat(db.Model):
    """ Aggregated stats for a flaky test in a specific day.

    The calculation is done periodically from the data in the test table. That is a
    moderately expensive operation we don't want to keep re-running.

    A flaky run for a test is one in which the test failed initially, and then
    passed when re-run.
    """
    __tablename__ = 'flakyteststat'
    __table_args__ = (
        Index('idx_flakyteststat_date', 'date'),
        UniqueConstraint('name', 'project_id', 'date', name='unq_name_per_project_per_day'),
    )

    id = Column(GUID, primary_key=True, default=uuid4)
    name = Column(Text, nullable=False)
    project_id = Column(GUID, ForeignKey('project.id', ondelete="CASCADE"), nullable=False)
    date = Column(Date, default=datetime.date.today, nullable=False)
    last_flaky_run_id = Column(GUID, ForeignKey('test.id', ondelete="CASCADE"), nullable=False)
    flaky_runs = Column(Integer, default=0, nullable=False)
    passing_runs = Column(Integer, default=0, nullable=False)
    first_run = Column(Date, default=datetime.date.today, nullable=False)

    project = relationship('Project')
    last_flaky_run = relationship('TestCase')

    def __init__(self, **kwargs):
        super(FlakyTestStat, self).__init__(**kwargs)
