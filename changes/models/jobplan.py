from __future__ import absolute_import

import logging
import uuid

from collections import defaultdict
from copy import deepcopy
from datetime import datetime
from flask import current_app
from sqlalchemy import Column, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.schema import Index

from changes.config import db
from changes.db.types.guid import GUID
from changes.db.types.json import JSONEncodedDict
from changes.db.utils import model_repr
from changes.utils.imports import import_string


BASH_BAZEL_SETUP = """
#!/bin/bash -eux
echo "%(apt_spec)s" | sudo tee /etc/apt/sources.list.d/bazel-changes-autogen.list
sudo apt-get update || true
sudo apt-get install -y --force-yes bazel drte-v1 gcc unzip zip
""".strip()


def get_bazel_setup():
    return BASH_BAZEL_SETUP % dict(
        apt_spec=current_app.config['APT_SPEC']
    )


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
            # It's important that we deepcopy data so any
            # mutations within the BuildStep don't propagate into the db
            return cls(**deepcopy(self.data))
        except Exception:
            return None


class JobPlan(db.Model):
    """
    A snapshot of a plan and its constituent steps, taken at job creation time.
    This exists so that running jobs are not impacted by configuration changes.
    Note that this table combines the data from the plan and step tables.
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
    snapshot_image_id = Column(GUID, ForeignKey('snapshot_image.id', ondelete="RESTRICT"), nullable=True)
    date_created = Column(DateTime, default=datetime.utcnow)
    date_modified = Column(DateTime, default=datetime.utcnow)
    data = Column(JSONEncodedDict)

    project = relationship('Project')
    build = relationship('Build')
    job = relationship('Job')
    plan = relationship('Plan')
    snapshot_image = relationship('SnapshotImage')

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
    def build_jobplan(cls, plan, job, snapshot_id=None):
        """Creates and returns a jobplan.

        Unless a snapshot_id is given, no snapshot will be used. This differs
        from the build index endpoint where the default is the current snapshot
        for a project.
        If a snapshot image is not found for a plan configured to use
        snapshots, a warning is given.
        """
        from changes.models.option import ItemOption
        from changes.models.snapshot import SnapshotImage

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
                HistoricalImmutableStep.from_step(s, options[s.id]).to_json()
                for s in plan_steps
            ],
            'options': options[plan.id],
        }

        snapshot_image_id = None
        # TODO(paulruan): Remove behavior that just having a snapshot plan means
        #                 snapshot use is enabled. Just `snapshot.allow` should be sufficient.
        allow_snapshot = '1' == options[plan.id].get('snapshot.allow', '0') or plan.snapshot_plan
        if allow_snapshot and snapshot_id is not None:
            snapshot_image = SnapshotImage.get(plan, snapshot_id)
            if snapshot_image is not None:
                snapshot_image_id = snapshot_image.id

            if snapshot_image is None:
                logging.warning("Failed to find snapshot_image for %s's %s.",
                                plan.project.slug, plan.label)

        instance = cls(
            plan_id=plan.id,
            job_id=job.id,
            build_id=job.build_id,
            project_id=job.project_id,
            snapshot_image_id=snapshot_image_id,
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
        from changes.models.job import Job
        from changes.models.project import ProjectConfigError
        from changes.buildsteps.lxc import LXCBuildStep

        job = Job.query.get(job_id)
        if job is None:
            return None, None

        if job.autogenerated:
            try:
                diff = job.source.patch.diff if job.source.patch else None
                project_config = job.project.get_config(job.source.revision_sha, diff=diff)
            except ProjectConfigError:
                logging.error('Project config for project %s is not in a valid format.', job.project.slug, exc_info=True)
                return None, None

            if 'bazel.targets' not in project_config:
                logging.error('Project config for project %s is missing `bazel.targets`. job: %s, revision_sha: %s, config: %s', job.project.slug, job.id, job.source.revision_sha, str(project_config), exc_info=True)
                return None, None

            bazel_test = 'bazel test ' + ' '.join(project_config['bazel.targets'])
            implementation = LXCBuildStep(
                commands=[
                    {'script': get_bazel_setup(), 'type': 'setup'},
                    {'script': bazel_test},
                ],
            )
            return None, implementation

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
