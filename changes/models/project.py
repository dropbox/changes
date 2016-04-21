import yaml

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


class ProjectConfigError(Exception):
    pass


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

    _default_config = {
        'build.file-blacklist': []
    }

    def get_config_path(self):
        # TODO in the future, get this file path from ProjectOption
        return '{}.yaml'.format(self.slug)

    def get_config(self, revision_sha, diff=None, config_path=None):
        '''Get the config for this project.

        Right now, the config lives at {slug}.yaml,
        at the root of the repository. This will change
        later on.

        The supplied config is applied on top of the default config
        (`_default_config`). In the case where the file is not found,
        the default config is returned.

        Args:
            revision_sha (str): The sha identifying the revision,
                                so the returned config is for that
                                revision.
            diff (str): The diff to apply before reading the config, used
                        for diff builds. Optional.
            config_path (str): The path of the config file

        Returns:
            dict - the config

        Raises:
            InvalidDiffError - When the supplied diff does not apply
            ProjectConfigError - When the config file is in an invalid format.
            NotImplementedError - When the project has no vcs backend
        '''
        # changes.vcs.base imports some models, which may lead to circular
        # imports, so let's import on-demand
        from changes.vcs.base import CommandError, ContentReadError
        if config_path is None:
            config_path = self.get_config_path()
        vcs = self.repository.get_vcs()
        if vcs is None:
            raise NotImplementedError
        else:
            try:
                config_content = vcs.read_file(
                    revision_sha, config_path, diff=diff)
            except (CommandError, ContentReadError):
                # this won't catch error when diff doesn't apply, which is good.
                config_content = '{}'
            try:
                config = yaml.safe_load(config_content)
                if not isinstance(config, dict):
                    raise ProjectConfigError(
                        'Invalid project config file {}'.format(config_path))
            except yaml.YAMLError:
                raise ProjectConfigError(
                    'Invalid project config file {}'.format(config_path))
        for k, v in self._default_config.iteritems():
            config.setdefault(k, v)
        return config


class ProjectOption(db.Model):
    """
    Key/value table storing configuration information for projects. Here
    is an incomplete list of possible keys:

        - build.branch-names
        - build.commit-trigger
        - build.expect-tests
        - build.file-whitelist
        - build.test-duration-warning
        - green-build.notify
        - green-build.project
        - mail.notify
        - mail.notify-addresses
        - mail.notify-addresses-revisions
        - mail.notify-author
        - phabricator.diff-trigger
        - phabricator.notify
        - phabricator.coverage
        - project.notes
        - project.owners
        - snapshot.current
        - ui.show-coverage
        - ui.show-tests
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
