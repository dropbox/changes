from datetime import datetime
from uuid import uuid4
from collections import defaultdict

from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Text
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import relationship, joinedload
from sqlalchemy.schema import UniqueConstraint
from changes.config import db
from changes.constants import ProjectStatus
from changes.db.types.guid import GUID
from changes.db.types.enum import Enum
from changes.utils.slugs import slugify


class Project(db.Model):
    """
    The way we organize changes. Each project is linked to one repository, and
    usually kicks off builds for it when new revisions come it (or just for
    some revisions based on filters.) Projects use build plans (see plan) to
    describe the work to be done for a build.
    """
    __tablename__ = 'project'

    id = Column(GUID, primary_key=True, default=uuid4)
    slug = Column(String(64), unique=True, nullable=False)
    repository_id = Column(GUID, ForeignKey('repository.id', ondelete="RESTRICT"), nullable=False)
    name = Column(String(64))
    date_created = Column(DateTime, default=datetime.utcnow)
    avg_build_time = Column(Integer)
    status = Column(Enum(ProjectStatus), default=ProjectStatus.active,
                    server_default='1')

    repository = relationship('Repository')
    plans = association_proxy('project_plans', 'plan')

    def __init__(self, **kwargs):
        super(Project, self).__init__(**kwargs)
        if not self.id:
            self.id = uuid4()
        if not self.slug:
            self.slug = slugify(self.name)

    @classmethod
    def get(cls, id):
        project = cls.query.options(
            joinedload(cls.repository, innerjoin=True),
        ).filter_by(slug=id).first()
        if project is None and len(id) == 32:
            project = cls.query.options(
                joinedload(cls.repository),
            ).get(id)
        return project


class ProjectOption(db.Model):
    """
    Key/value table storing configuration information for projects. Here
    is an incomplete list of possible keys:

        mail.notify-addresses-revisions
        build.expect-tests
        build.commit-trigger
        ui.show-coverage
        project.owners
        mail.notify-addresses
        snapshot.current
        mail.notify
        build.test-duration-warning
        green-build.notify
        phabricator.notify
        mail.notify-author
        project.notes
        ui.show-tests
        green-build.project
        build.file-whitelist
        build.branch-names
        phabricator.diff-trigger
    """
    __tablename__ = 'projectoption'
    __table_args__ = (
        UniqueConstraint('project_id', 'name', name='unq_projectoption_name'),
    )

    id = Column(GUID, primary_key=True, default=uuid4)
    project_id = Column(GUID, ForeignKey('project.id', ondelete="CASCADE"), nullable=False)
    name = Column(String(64), nullable=False)
    value = Column(Text, nullable=False)
    date_created = Column(DateTime, default=datetime.utcnow, nullable=False)

    project = relationship('Project')

    def __init__(self, **kwargs):
        super(ProjectOption, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid4()
        if self.date_created is None:
            self.date_created = datetime.utcnow()


class ProjectOptionsHelper:
    @staticmethod
    def get_options(project_list, options_list):
        options_query = db.session.query(
            ProjectOption.project_id, ProjectOption.name, ProjectOption.value
        ).filter(
            ProjectOption.project_id.in_(p.id for p in project_list),
            ProjectOption.name.in_(options_list)
        )

        options = defaultdict(dict)
        for project_id, option_name, option_value in options_query:
            options[project_id][option_name] = option_value

        return options
