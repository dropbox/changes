from __future__ import absolute_import

import mock
import json
import unittest2

from exam import Exam, fixture
from flask import current_app as app
from uuid import uuid4

from changes.config import db, mail
from changes.models import (
    Repository, Job, Project, Revision, RemoteEntity, Change, Author,
    TestGroup, Patch, Plan, Step, BuildFamily
)


SAMPLE_DIFF = """diff --git a/README.rst b/README.rst
index 2ef2938..ed80350 100644
--- a/README.rst
+++ b/README.rst
@@ -1,5 +1,5 @@
 Setup
------
+====="""


class Fixtures(object):
    def create_repo(self, **kwargs):
        kwargs.setdefault('url', 'http://example.com/{0}'.format(uuid4().hex))

        repo = Repository(**kwargs)
        db.session.add(repo)

        return repo

    def create_project(self, **kwargs):
        if not kwargs.get('repository'):
            kwargs['repository'] = self.create_repo()
        kwargs.setdefault('name', uuid4().hex)
        kwargs.setdefault('slug', kwargs['name'])

        project = Project(**kwargs)
        db.session.add(project)

        return project

    def create_change(self, project, **kwargs):
        kwargs.setdefault('label', 'Sample')

        change = Change(
            hash=uuid4().hex,
            repository=project.repository,
            project=project,
            **kwargs
        )
        db.session.add(change)

        return change

    def create_testgroup(self, build, **kwargs):
        kwargs.setdefault('name', uuid4().hex)

        group = TestGroup(
            build=build,
            project=build.project,
            **kwargs
        )
        db.session.add(group)

        return group

    def create_build(self, project, **kwargs):
        revision_sha = kwargs.pop('revision_sha', uuid4().hex)
        revision = Revision.query.filter_by(
            sha=revision_sha, repository=project.repository).first()
        if not revision:
            revision = Revision(
                sha=revision_sha,
                repository=project.repository
            )
            db.session.add(revision)

        if kwargs.get('change', False) is False:
            kwargs['change'] = self.create_change(project)

        kwargs.setdefault('label', 'Sample')

        build = Job(
            repository_id=project.repository_id,
            repository=project.repository,
            project_id=project.id,
            project=project,
            revision_sha=revision.sha,
            **kwargs
        )
        db.session.add(build)

        return build

    def create_patch(self, project, **kwargs):
        kwargs.setdefault('label', 'Test Patch')
        kwargs.setdefault('message', 'Hello world!')
        kwargs.setdefault('diff', SAMPLE_DIFF)
        kwargs.setdefault('parent_revision_sha', uuid4().hex)
        if not kwargs.get('repository'):
            kwargs['repository'] = self.create_repo()

        patch = Patch(project=project, **kwargs)
        db.session.add(patch)

        return patch

    def create_revision(self, **kwargs):
        kwargs.setdefault('sha', uuid4().hex)
        if not kwargs.get('repository'):
            kwargs['repository'] = self.create_repo()

        if not kwargs.get('author'):
            kwargs['author'] = self.create_author()

        kwargs.setdefault('message', 'Test message')

        revision = Revision(**kwargs)
        db.session.add(revision)

        return revision

    def create_author(self, email=None, **kwargs):
        if not email:
            email = uuid4().hex + '@example.com'
        kwargs.setdefault('name', 'Test Case')

        author = Author(email=email, **kwargs)
        db.session.add(author)

        return author

    def create_plan(self, **kwargs):
        kwargs.setdefault('label', 'test')

        plan = Plan(**kwargs)
        db.session.add(plan)

        return plan

    def create_step(self, plan, **kwargs):
        kwargs.setdefault('implementation', 'test')
        kwargs.setdefault('order', 0)

        step = Step(plan=plan, **kwargs)
        db.session.add(step)

        return step

    def create_buildfamily_from_build(self, build):
        family = BuildFamily(
            project=build.project,
            repository=build.repository,
            status=build.status,
            author=build.author,
            label=build.label,
            target=build.target,
            revision_sha=build.revision_sha,
            message=build.message,
        )
        db.session.add(family)

        return family


class TestCase(Exam, unittest2.TestCase, Fixtures):
    def setUp(self):
        self.repo = self.create_repo(
            url='https://github.com/dropbox/changes.git',
        )
        self.project = self.create_project(
            repository=self.repo,
            name='test',
            slug='test'
        )
        self.project2 = self.create_project(
            repository=self.repo,
            name='test2',
            slug='test2',
        )

        # disable commit
        self.patcher = mock.patch('changes.config.db.session.commit')
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

        # mock out mail
        mail_context = mail.record_messages()
        self.outbox = mail_context.__enter__()
        self.addCleanup(lambda: mail_context.__exit__(None, None, None))

        super(TestCase, self).setUp()

    @fixture
    def client(self):
        return app.test_client()

    def unserialize(self, response):
        assert response.headers['Content-Type'] == 'application/json'
        return json.loads(response.data)


class BackendTestCase(TestCase):
    backend_cls = None
    backend_options = {}
    provider = None

    def get_backend(self):
        return self.backend_cls(
            app=app, **self.backend_options
        )

    def make_entity(self, type, internal_id, remote_id):
        entity = RemoteEntity(
            type=type,
            remote_id=remote_id,
            internal_id=internal_id,
            provider=self.provider,
        )
        db.session.add(entity)
        return entity


class APITestCase(TestCase):
    def setUp(self):
        from changes.backends.base import BaseBackend

        super(APITestCase, self).setUp()

        self.mock_backend = mock.Mock(
            spec=BaseBackend(app=app),
        )
        self.patcher = mock.patch(
            'changes.api.base.APIView.get_backend',
            mock.Mock(return_value=self.mock_backend))
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
