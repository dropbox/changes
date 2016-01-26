from changes.constants import Cause
from changes.lib import build_type
from changes.testutils.cases import TestCase


def add_tag(b, tag):
    prev = b.tags or []
    prev.append(tag)
    b.tags = prev
    return b


class BuildTypeTestCase(TestCase):

    def setUp(self):
        super(BuildTypeTestCase, self).setUp()
        self.project = self.create_project(name='test', slug='test')

    def _plain_commit_build(self):
        build = self.create_build(
            self.project,
            label='Test diff',
        )
        return build

    def _tagged_commit_build(self):
        b = self._plain_commit_build()
        b.tags = ['commit']
        return b

    def _tagged_cq_build(self):
        b = self._plain_commit_build()
        b.tags = ['commit-queue']
        return b

    def _snapshot_build(self):
        b = self._plain_commit_build()
        b.cause = Cause.snapshot
        return b

    def _plain_patch_build(self):
        patch = self.create_patch()
        patch_source = self.create_source(self.project, patch=patch)
        patch_build = self.create_build(
            self.project,
            label='Test',
            source=patch_source,
        )
        return patch_build

    def _arc_test_build(self):
        b = self._plain_patch_build()
        return add_tag(b, 'arc test')

    def test_is_any_commit_build(self):
        assert build_type.is_any_commit_build(self._plain_commit_build())
        assert build_type.is_any_commit_build(self._tagged_commit_build())
        assert not build_type.is_any_commit_build(self._tagged_cq_build())
        assert not build_type.is_any_commit_build(self._snapshot_build())
        assert not build_type.is_any_commit_build(self._plain_patch_build())
        assert not build_type.is_any_commit_build(add_tag(self._plain_patch_build(), 'commit'))

    def test_is_initial_commit_build(self):
        assert not build_type.is_initial_commit_build(self._plain_commit_build())
        assert build_type.is_initial_commit_build(self._tagged_commit_build())
        assert not build_type.is_initial_commit_build(self._tagged_cq_build())
        assert not build_type.is_initial_commit_build(self._snapshot_build())
        assert not build_type.is_initial_commit_build(self._plain_patch_build())
        assert not build_type.is_initial_commit_build(add_tag(self._plain_patch_build(), 'commit'))

    def test_is_arc_test_build(self):
        assert not build_type.is_arc_test_build(self._plain_commit_build())
        assert not build_type.is_arc_test_build(self._plain_patch_build())
        assert build_type.is_arc_test_build(self._arc_test_build())
