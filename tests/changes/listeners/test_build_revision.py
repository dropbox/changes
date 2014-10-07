from __future__ import absolute_import, print_function

from mock import Mock, patch

from changes.config import db
from changes.listeners.build_revision import revision_created_handler
from changes.models import Build, ProjectOption
from changes.testutils.cases import TestCase
from changes.testutils.fixtures import SAMPLE_DIFF


class RevisionCreatedHandlerTestCase(TestCase):
    def test_simple(self):
        repo = self.create_repo()
        revision = self.create_revision(repository=repo)
        project = self.create_project(repository=repo)
        plan = self.create_plan()
        plan.projects.append(project)

        revision_created_handler(revision_sha=revision.sha, repository_id=repo.id)

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
        db.session.flush()

        revision_created_handler(revision_sha=revision.sha, repository_id=repo.id)

        assert not Build.query.first()

    @patch('changes.models.Repository.get_vcs')
    @patch('changes.api.build_index.identify_revision')
    def test_file_whitelist(self, mock_identify_revision, mock_get_vcs):
        repo = self.create_repo()
        revision = self.create_revision(repository=repo)
        project = self.create_project(repository=repo)
        plan = self.create_plan()
        plan.projects.append(project)

        option = ProjectOption(project=project, name='build.file-whitelist', value='foo.txt')

        mock_vcs = Mock()
        mock_vcs.export.return_value = SAMPLE_DIFF
        mock_identify_revision.return_value = revision
        mock_get_vcs.return_value = mock_vcs

        db.session.add(option)
        db.session.flush()

        revision_created_handler(revision_sha=revision.sha, repository_id=repo.id)

        mock_vcs.export.assert_called_once_with(revision.sha)

        assert not Build.query.first()

        option.value = 'ci/*'
        db.session.add(option)
        db.session.flush()

        revision_created_handler(revision_sha=revision.sha, repository_id=repo.id)

        mock_identify_revision.assert_called_once_with(repo, revision.sha)

        assert Build.query.first()
