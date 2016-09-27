from changes.constants import Status
from changes.lib.revision_lib import get_latest_finished_build_for_revision, get_child_revisions
from changes.testutils.cases import TestCase


class GetLatestFinishedCommitBuildTestCase(TestCase):
    def test_correct(self):
        project = self.create_project()
        source = self.create_source(project)
        diff_source = self.create_source(project, revision_sha=source.revision_sha, patch=self.create_patch())
        self.create_build(source=source, status=Status.finished, project=project)
        self.create_build(source=source, status=Status.finished, project=project)
        latest_build = self.create_build(source=source, project=project)
        self.create_build(source=source, status=Status.in_progress, project=project)  # in progress
        self.create_build(source=diff_source, status=Status.finished, project=project)  # diff build
        self.create_build(status=Status.finished, project=project)  # different commit

        assert get_latest_finished_build_for_revision(source.revision_sha, project.id)


class GetChildRevisions(TestCase):
    def test_correct(self):
        repository = self.create_repo()
        parent1 = self.create_revision(repository=repository)
        parent2 = self.create_revision(repository=repository)
        child1 = self.create_revision(parents=[parent2.sha], repository=repository)
        child2 = self.create_revision(parents=[parent1.sha, parent2.sha], repository=repository)
        self.create_revision(parents=[parent1.sha])  # different repo

        assert get_child_revisions(parent1) == [child2]
        assert set(get_child_revisions(parent2)) == set([child1, child2])
