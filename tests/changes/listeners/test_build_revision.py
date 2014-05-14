from changes.config import db
from changes.listeners.build_revision import revision_created_handler
from changes.models import Build, ProjectOption
from changes.testutils.cases import TestCase


class RevisionCreatedHandlerTestCase(TestCase):
    def test_simple(self):
        repo = self.create_repo()
        revision = self.create_revision(repository=repo)
        project = self.create_project(repository=repo)
        plan = self.create_plan()
        plan.projects.append(project)

        revision_created_handler(revision)

        build_list = list(Build.query.filter(
            Build.project == project,
        ))

        assert len(build_list) == 1

    def test_disabled(self):
        repo = self.create_repo()
        revision = self.create_revision(repository=repo)
        project = self.create_project(repository=repo)
        plan = self.create_plan()
        plan.projects.append(project)

        db.session.add(ProjectOption(project=project, name='build.commit-trigger', value='0'))
        db.session.commit()

        revision_created_handler(revision)

        assert not Build.query.first()
