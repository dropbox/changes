from __future__ import absolute_import

import uuid

from collections import defaultdict
from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.schema import Index

from changes.config import db
from changes.db.types.guid import GUID
from changes.db.types.json import JSONEncodedDict
from changes.db.utils import model_repr
from changes.utils.imports import import_string


class HistoricalImmutableStep(object):
    def __init__(self, id, implementation, data, order, options=None):
        self.id = id
        self.implementation = implementation
        self.data = data
        self.order = order
        self.options = options or {}

    @classmethod
    def from_step(cls, step, options=None):
        return cls(
            id=step.id.hex,
            implementation=step.implementation,
            data=dict(step.data),
            order=step.order,
            options=options,
        )

    def to_json(self):
        return {
            'id': self.id,
            'implementation': self.implementation,
            'data': self.data,
            'order': self.order,
            'options': self.options,
        }

    def get_implementation(self, load=True):
        try:
            cls = import_string(self.implementation)
        except Exception:
            return None

        if not load:
            return cls

        try:
            return cls(**self.data)
        except Exception:
            return None


class JobPlan(db.Model):
    """
    A link to all Job + Plan's for a Build.

    TODO(dcramer): this should include a snapshot of the plan at build time.
    """
    __tablename__ = 'jobplan'
    __table_args__ = (
        Index('idx_buildplan_project_id', 'project_id'),
        Index('idx_buildplan_family_id', 'build_id'),
        Index('idx_buildplan_plan_id', 'plan_id'),
    )

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    project_id = Column(GUID, ForeignKey('project.id', ondelete="CASCADE"), nullable=False)
    build_id = Column(GUID, ForeignKey('build.id', ondelete="CASCADE"), nullable=False)
    job_id = Column(GUID, ForeignKey('job.id', ondelete="CASCADE"), nullable=False, unique=True)
    plan_id = Column(GUID, ForeignKey('plan.id', ondelete="CASCADE"), nullable=False)
    date_created = Column(DateTime, default=datetime.utcnow)
    date_modified = Column(DateTime, default=datetime.utcnow)
    data = Column(JSONEncodedDict)

    project = relationship('Project')
    build = relationship('Build')
    job = relationship('Job')
    plan = relationship('Plan')

    __repr__ = model_repr('build_id', 'job_id', 'plan_id')

    def __init__(self, **kwargs):
        super(JobPlan, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid.uuid4()
        if self.date_created is None:
            self.date_created = datetime.utcnow()
        if self.date_modified is None:
            self.date_modified = self.date_created

    def get_steps(self):
        if 'snapshot' in self.data:
            return map(lambda x: HistoricalImmutableStep(**x), self.data['snapshot']['steps'])
        return map(HistoricalImmutableStep.from_step, self.plan.steps)

    # TODO(dcramer): find a better place for this
    @classmethod
    def build_jobplan(cls, plan, job):
        from changes.models import ItemOption

        plan_steps = sorted(plan.steps, key=lambda x: x.order)

        option_item_ids = [s.id for s in plan_steps]
        option_item_ids.append(plan.id)

        options = defaultdict(dict)
        options_query = db.session.query(
            ItemOption.item_id, ItemOption.name, ItemOption.value
        ).filter(
            ItemOption.item_id.in_(option_item_ids),
        )
        for item_id, opt_name, opt_value in options_query:
            options[item_id][opt_name] = opt_value

        snapshot = {
            'steps': [
                HistoricalImmutableStep.from_step(s, options[s]).to_json()
                for s in plan_steps
            ],
            'options': options[plan.id]
        }

        instance = cls(
            plan_id=plan.id,
            job_id=job.id,
            build_id=job.build_id,
            project_id=job.project_id,
            data={
                'snapshot': snapshot,
            },
        )

        return instance

    # TODO(dcramer): this is a temporary method and should be removed once we
    # support more than a single job (it also should not be contained within
    # the model file)
    @classmethod
    def get_build_step_for_job(cls, job_id):
        jobplan = cls.query.filter(
            cls.job_id == job_id,
        ).first()
        if jobplan is None:
            return None, None

        steps = jobplan.get_steps()
        try:
            step = steps[0]
        except IndexError:
            return jobplan, None

        return jobplan, step.get_implementation()
