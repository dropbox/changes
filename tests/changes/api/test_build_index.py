import json
import uuid
import yaml

from cStringIO import StringIO
from datetime import datetime

from mock import patch, MagicMock, Mock
from changes.api.build_index import find_green_parent_sha
from changes.config import db
from changes.constants import Cause, Status, Result
from changes.models.build import Build
from changes.models.job import Job
from changes.models.jobplan import JobPlan
from changes.models.patch import Patch
from changes.models.plan import PlanStatus
from changes.models.project import ProjectOption
from changes.models.snapshot import SnapshotStatus
from changes.testutils import APITestCase, TestCase, SAMPLE_DIFF, SAMPLE_DIFF_BYTES
from changes.vcs.base import CommandError, InvalidDiffError, RevisionResult, Vcs, UnknownRevision
from changes.testutils.build import CreateBuildsMixin


class FindGreenParentShaTest(TestCase):
    # TODO(dcramer): we should add checks for builds from other projects
    # as they shouldn't be included with the green build query
    def test_current_green(self):
        project = self.create_project()
        current_source = self.create_source(
            project=project,
            revision_sha='a' * 40,
        )
        newer_source = self.create_source(
            project=project,
            revision_sha='b' * 40,
        )
        current_build = self.create_build(  # NOQA
            project=project,
            source=current_source,
            status=Status.finished,
            result=Result.passed,
        )
        newer_build = self.create_build(  # NOQA
            project=project,
            source=newer_source,
            status=Status.finished,
            result=Result.passed,
        )

        result = find_green_parent_sha(project, current_source.revision_sha)
        assert result == current_source.revision_sha

    def test_newer_green(self):
        project = self.create_project()
        older_source = self.create_source(
            project=project,
            revision_sha='c' * 40,
        )
        current_source = self.create_source(
            project=project,
            revision_sha='a' * 40,
        )
        newer_source = self.create_source(
            project=project,
            revision_sha='b' * 40,
        )
        older_build = self.create_build(  # NOQA
            project=project,
            source=older_source,
            status=Status.finished,
            result=Result.passed,
        )
        current_build = self.create_build(  # NOQA
            project=project,
            source=current_source,
            status=Status.finished,
            result=Result.failed,
        )
        newer_build = self.create_build(  # NOQA
            project=project,
            source=newer_source,
            status=Status.finished,
            result=Result.passed,
        )
        result = find_green_parent_sha(project, current_source.revision_sha)
        assert result == newer_source.revision_sha

    def test_newer_green_missing_revision(self):
        project = self.create_project()
        current_source = self.create_source(
            project=project,
            revision_sha='a' * 40,
        )
        newer_source = self.create_source(
            project=project,
            revision_sha=None,
        )
        newer_build = self.create_build(  # NOQA
            project=project,
            source=newer_source,
            status=Status.finished,
            result=Result.passed,
        )
        result = find_green_parent_sha(project, current_source.revision_sha)
        assert result == current_source.revision_sha

    def test_newer_green_is_patch(self):
        project = self.create_project()
        current_source = self.create_source(
            project=project,
            revision_sha='a' * 40,
        )
        newer_source = self.create_source(
            project=project,
            revision_sha='b' * 40,
            patch=self.create_patch(repository=project.repository),
        )
        newer_build = self.create_build(  # NOQA
            project=project,
            source=newer_source,
            status=Status.finished,
            result=Result.passed,
        )
        result = find_green_parent_sha(project, current_source.revision_sha)
        assert result == current_source.revision_sha

    def test_without_newer_green(self):
        project = self.create_project()
        older_source = self.create_source(
            project=project,
            revision_sha='c' * 40,
        )
        current_source = self.create_source(
            project=project,
            revision_sha='a' * 40,
        )
        newer_source = self.create_source(
            project=project,
            revision_sha='b' * 40,
        )
        older_build = self.create_build(  # NOQA
            project=project,
            source=older_source,
            status=Status.finished,
            result=Result.passed,
        )
        current_build = self.create_build(  # NOQA
            project=project,
            source=current_source,
            status=Status.finished,
            result=Result.failed,
        )
        newer_build = self.create_build(  # NOQA
            project=project,
            source=newer_source,
            status=Status.finished,
            result=Result.failed,
        )
        result = find_green_parent_sha(project, current_source.revision_sha)
        assert result == current_source.revision_sha

    def test_without_any_builds(self):
        project = self.create_project()
        result = find_green_parent_sha(project, 'a' * 40)
        assert result == 'a' * 40


class BuildListTest(APITestCase):
    path = '/api/0/builds/'

    def test_simple(self):
        project = self.create_project()
        project2 = self.create_project()
        build = self.create_build(project)
        build2 = self.create_build(project2)

        resp = self.client.get(self.path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 2
        assert data[0]['id'] == build2.id.hex
        assert data[1]['id'] == build.id.hex

    def test_tag_query(self):
        project = self.create_project()
        build1 = self.create_build(project, tags=['foo'])
        build2 = self.create_build(project, tags=['bar'])

        resp = self.client.get(self.path + '?tag=foo')
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == build1.id.hex


class BuildCreateTest(APITestCase, CreateBuildsMixin):
    path = '/api/0/builds/'

    def setUp(self):
        self.project = self.create_project()
        self.plan = self.create_plan(self.project)
        db.session.commit()
        super(BuildCreateTest, self).setUp()

    def get_fake_vcs(self, log_results=None):
        def _log_results(parent=None, branch=None, offset=0, limit=1):
            assert not branch
            return iter([
                RevisionResult(
                    id='a' * 40,
                    message='hello world',
                    author='Foo <foo@example.com>',
                    author_date=datetime.utcnow(),
                )])
        if log_results is None:
            log_results = _log_results
        # Fake having a VCS and stub the returned commit log
        fake_vcs = Mock(spec=Vcs)
        fake_vcs.read_file.side_effect = CommandError(cmd="test command", retcode=128)
        fake_vcs.exists.return_value = True
        fake_vcs.log.side_effect = UnknownRevision(cmd="test command", retcode=128)
        fake_vcs.export.side_effect = UnknownRevision(cmd="test command", retcode=128)
        fake_vcs.get_changed_files.side_effect = UnknownRevision(cmd="test command", retcode=128)

        def fake_update():
            # this simulates the effect of calling update() on a repo,
            # mainly that `export` and `log` now works.
            fake_vcs.log.side_effect = log_results
            fake_vcs.export.side_effect = None
            fake_vcs.export.return_value = SAMPLE_DIFF_BYTES
            fake_vcs.get_changed_files.side_effect = lambda id: Vcs.get_changed_files(fake_vcs, id)

        fake_vcs.update.side_effect = fake_update

        return fake_vcs

    def test_minimal(self):
        resp = self.client.post(self.path, data={
            'sha': 'a' * 40,
            'project': self.project.slug,
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id']

        job = Job.query.filter(
            Job.build_id == data[0]['id']
        ).first()
        build = job.build
        source = build.source

        assert build.cause == Cause.unknown
        assert job.project == self.project

        assert source.repository_id == self.project.repository_id
        assert source.revision_sha == 'a' * 40

    def test_manual_cause(self):
        resp = self.client.post(self.path, data={
            'sha': 'a' * 40,
            'project': self.project.slug,
            'cause': 'manual',
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id']

        build_id = data[0]['id']
        b = Build.query.get(build_id)
        assert b.cause == Cause.manual

    def test_explicit_unknown_cause(self):
        resp = self.client.post(self.path, data={
            'sha': 'a' * 40,
            'project': self.project.slug,
            'cause': 'unknown',
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id']

        build_id = data[0]['id']
        b = Build.query.get(build_id)
        assert b.cause == Cause.unknown

    def test_bad_causes(self):
        ss_resp = self.client.post(self.path, data={
            'sha': 'a' * 40,
            'project': self.project.slug,
            'cause': 'snapshot',
        })
        assert ss_resp.status_code == 400

        nonsense_resp = self.client.post(self.path, data={
            'sha': 'a' * 40,
            'project': self.project.slug,
            'cause': 'this_is_not_a_real_cause',
        })
        assert nonsense_resp.status_code == 400

    def test_with_snapshot(self):
        snapshot = self.create_snapshot(self.project, status=SnapshotStatus.active)
        image = self.create_snapshot_image(
            plan=self.plan,
            snapshot=snapshot,
        )
        self.create_option(
            item_id=self.plan.id,
            name='snapshot.allow',
            value='1'
        )
        db.session.commit()

        resp = self.client.post(self.path, data={
            'sha': 'a' * 40,
            'project': self.project.slug,
            'snapshot_id': snapshot.id.hex,
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id']

        job = Job.query.filter(
            Job.build_id == data[0]['id']
        ).first()
        build = job.build
        source = build.source

        assert job.project == self.project

        assert source.repository_id == self.project.repository_id
        assert source.revision_sha == 'a' * 40

        jobplan = JobPlan.query.filter(
            JobPlan.build_id == data[0]['id'],
            JobPlan.job_id == job.id
        ).first()

        assert jobplan.snapshot_image_id == image.id

    def test_default_to_current_snapshot(self):
        snapshot = self.create_snapshot(self.project, status=SnapshotStatus.active)
        image = self.create_snapshot_image(
            plan=self.plan,
            snapshot=snapshot,
        )
        self.create_option(
            item_id=self.plan.id,
            name='snapshot.allow',
            value='1'
        )
        self.create_project_option(
            project=self.project,
            name='snapshot.current',
            value=snapshot.id.hex
        )
        db.session.commit()

        resp = self.client.post(self.path, data={
            'sha': 'a' * 40,
            'project': self.project.slug,
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        job = Job.query.filter(
            Job.build_id == data[0]['id']
        ).first()
        jobplan = JobPlan.query.filter(
            JobPlan.build_id == data[0]['id'],
            JobPlan.job_id == job.id
        ).first()

        assert jobplan.snapshot_image_id == image.id

    def test_no_snapshot_option(self):
        snapshot = self.create_snapshot(self.project, status=SnapshotStatus.active)
        image = self.create_snapshot_image(
            plan=self.plan,
            snapshot=snapshot,
        )
        self.create_option(
            item_id=self.plan.id,
            name='snapshot.allow',
            value='1'
        )
        self.create_project_option(
            project=self.project,
            name='snapshot.current',
            value=snapshot.id.hex
        )
        db.session.commit()

        resp = self.client.post(self.path, data={
            'sha': 'a' * 40,
            'project': self.project.slug,
            'no_snapshot': '1',
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        job = Job.query.filter(
            Job.build_id == data[0]['id']
        ).first()
        jobplan = JobPlan.query.filter(
            JobPlan.build_id == data[0]['id'],
            JobPlan.job_id == job.id
        ).first()

        assert jobplan.snapshot_image_id is None

    def test_with_nonexistent_snapshot(self):
        self.create_option(
            item_id=self.plan.id,
            name='snapshot.allow',
            value='1'
        )
        db.session.commit()

        resp = self.client.post(self.path, data={
            'sha': 'a' * 40,
            'project': self.project.slug,
            'snapshot_id': uuid.uuid4().hex,
        })
        assert resp.status_code == 400

        data = self.unserialize(resp)
        assert 'Unable to find snapshot' in data['error']

    def test_with_pending_snapshot(self):
        snapshot = self.create_snapshot(self.project, status=SnapshotStatus.pending)
        image = self.create_snapshot_image(
            plan=self.plan,
            snapshot=snapshot,
        )
        self.create_option(
            item_id=self.plan.id,
            name='snapshot.allow',
            value='1'
        )
        db.session.commit()

        resp = self.client.post(self.path, data={
            'sha': 'a' * 40,
            'project': self.project.slug,
            'snapshot_id': snapshot.id.hex,
        })
        assert resp.status_code == 400

        data = self.unserialize(resp)
        assert 'Snapshot is in an invalid state' in data['error']

    def test_with_snapshot_missing_image(self):
        snapshot = self.create_snapshot(self.project, status=SnapshotStatus.active)
        image = self.create_snapshot_image(
            plan=self.plan,
            snapshot=snapshot,
        )
        self.create_option(
            item_id=self.plan.id,
            name='snapshot.allow',
            value='1'
        )

        # another_plan has snapshots enabled but the snapshot does not have an image for it
        # so trying to start a build using the snapshot should fail.
        another_plan = self.create_plan(self.project)
        self.create_option(
            item_id=another_plan.id,
            name='snapshot.allow',
            value='1'
        )
        db.session.commit()

        resp = self.client.post(self.path, data={
            'sha': 'a' * 40,
            'project': self.project.slug,
            'snapshot_id': snapshot.id.hex,
        })
        assert resp.status_code == 400

        data = self.unserialize(resp)
        assert 'Snapshot cannot be applied' in data['error']

        data = self.unserialize(resp)

        # However, it's fine if it's not an active plan.
        another_plan.status = PlanStatus.inactive
        db.session.add(another_plan)
        db.session.commit()

        resp = self.client.post(self.path, data={
            'sha': 'a' * 40,
            'project': self.project.slug,
            'snapshot_id': snapshot.id.hex,
        })
        assert resp.status_code == 200

    def test_require_snapshot(self):
        snapshot = self.create_snapshot(self.project, status=SnapshotStatus.active)
        image = self.create_snapshot_image(
            plan=self.plan,
            snapshot=snapshot,
        )
        self.create_project_option(
            project=self.project,
            name='snapshot.current',
            value=snapshot.id.hex
        )
        self.create_option(
            item_id=self.plan.id,
            name='snapshot.allow',
            value='1'
        )

        # another_plan has snapshots enabled but the snapshot does not have an
        # image for it. so trying to start a build using the default snapshot
        # should not create a job for this plan.
        another_plan = self.create_plan(self.project)
        self.create_option(
            item_id=another_plan.id,
            name='snapshot.allow',
            value='1'
        )
        self.create_option(
            item_id=another_plan.id,
            name='snapshot.require',
            value='1'
        )
        db.session.commit()

        resp = self.client.post(self.path, data={
            'sha': 'a' * 40,
            'project': self.project.slug,
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id']

        jobs = Job.query.filter(
            Job.build_id == data[0]['id']
        ).all()
        assert len(jobs) == 1

        # Then if we create a snapshot image for the second plan, then there
        # should be jobs for both plans.
        another_image = self.create_snapshot_image(
            plan=another_plan,
            snapshot=snapshot,
        )
        db.session.commit()

        resp = self.client.post(self.path, data={
            'sha': 'a' * 40,
            'project': self.project.slug,
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id']

        jobs = Job.query.filter(
            Job.build_id == data[0]['id']
        ).all()
        assert len(jobs) == 2

    @patch('changes.models.Repository.get_vcs')
    def test_defaults_to_revision(self, get_vcs):
        fake_vcs = self.get_fake_vcs()
        fake_vcs.update.side_effect = None
        get_vcs.return_value = fake_vcs
        revision = self.create_revision(
            repository=self.project.repository,
            sha='a' * 40,
        )
        resp = self.client.post(self.path, data={
            'sha': 'a' * 40,
            'project': self.project.slug,
            'apply_project_files_trigger': '',  # requires git, which we disabled
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id']

        job = Job.query.filter(
            Job.build_id == data[0]['id']
        ).first()
        build = job.build
        source = build.source

        assert build.message == revision.message
        assert build.author == revision.author
        assert build.label == revision.subject

        assert job.project == self.project

        assert source.repository_id == self.project.repository_id
        assert source.revision_sha == 'a' * 40

    @patch('changes.models.Repository.get_vcs')
    def test_defaults_to_revision_not_found(self, get_vcs):
        fake_vcs = self.get_fake_vcs()
        fake_vcs.update.side_effect = None
        get_vcs.return_value = fake_vcs
        revision = self.create_revision(
            repository=self.project.repository,
            sha='a' * 40,
        )
        resp = self.client.post(self.path, data={
            'sha': 'a' * 40,
            'project': self.project.slug,
            'apply_project_files_trigger': '1',  # This requires that git be updated
        })
        assert resp.status_code == 400
        data = self.unserialize(resp)
        assert 'error' in data
        assert 'problems' in data
        assert 'sha' in data['problems']
        assert 'repository' in data['problems']

    @patch('changes.models.Repository.get_vcs')
    def test_error_on_invalid_revision(self, get_vcs):
        def log_results(parent=None, branch=None, offset=0, limit=1):
            assert not branch
            ret = MagicMock()
            ret.next.side_effect = UnknownRevision(cmd="test command", retcode=128)
            return ret

        # Fake having a VCS and stub the returned commit log
        get_vcs.return_value = self.get_fake_vcs(log_results=log_results)

        # try any commit sha, since we mocked out log_results
        resp = self.client.post(self.path, data={
            'sha': 'z' * 40,
            'project': self.project.slug,
        })
        assert resp.status_code == 400
        data = self.unserialize(resp)
        assert 'error' in data
        assert 'problems' in data
        assert 'sha' in data['problems']

    def post_sample_patch(self, data=None):
        if data is None:
            data = {}
        data['project'] = self.project.slug
        data['sha'] = 'a' * 40
        data['target'] = 'D1234'
        data['label'] = 'Foo Bar'
        data['message'] = 'Hello world!'
        data['author'] = 'David Cramer <dcramer@example.com>'
        data['patch'] = (StringIO(SAMPLE_DIFF_BYTES), 'foo.diff')
        data['patch[data]'] = '{"foo": "bar"}'
        return self.client.post(self.path, data=data)

    @patch('changes.models.Repository.get_vcs')
    def test_when_not_in_whitelist_diff_build(self, get_vcs):
        po = ProjectOption(
            project=self.project,
            name='build.file-whitelist',
            value='nonexisting_directory',
        )
        db.session.add(po)
        db.session.commit()
        get_vcs.return_value = self.get_fake_vcs()

        resp = self.post_sample_patch({
            'apply_project_files_trigger': '1',
        })
        assert resp.status_code == 200, resp.data
        data = self.unserialize(resp)
        assert len(data) == 0

    @patch('changes.models.Repository.get_vcs')
    def test_when_in_whitelist_diff_build(self, get_vcs):
        po = ProjectOption(
            project=self.project,
            name='build.file-whitelist',
            value='ci/*',
        )
        db.session.add(po)
        db.session.commit()
        get_vcs.return_value = self.get_fake_vcs()

        resp = self.post_sample_patch({
            'apply_project_files_trigger': '1',
        })
        assert resp.status_code == 200, resp.data
        data = self.unserialize(resp)
        assert len(data) == 1

    @patch('changes.models.Repository.get_vcs')
    def test_when_in_whitelist_diff_build_default_true(self, get_vcs):
        po = ProjectOption(
            project=self.project,
            name='build.file-whitelist',
            value='ci/*',
        )
        db.session.add(po)
        db.session.commit()
        get_vcs.return_value = self.get_fake_vcs()

        resp = self.post_sample_patch()
        assert resp.status_code == 200, resp.data
        data = self.unserialize(resp)
        assert len(data) == 1

    @patch('changes.models.Repository.get_vcs')
    def test_when_in_whitelist_diff_build_default_true_negative(self, get_vcs):
        po = ProjectOption(
            project=self.project,
            name='build.file-whitelist',
            value='nonexisting_directory',
        )
        db.session.add(po)
        db.session.commit()
        get_vcs.return_value = self.get_fake_vcs()

        resp = self.post_sample_patch()
        assert resp.status_code == 200, resp.data
        data = self.unserialize(resp)
        assert len(data) == 0

    @patch('changes.models.Repository.get_vcs')
    def test_when_not_in_whitelist_commit_build(self, get_vcs):
        po = ProjectOption(
            project=self.project,
            name='build.file-whitelist',
            value='nonexisting_directory',
        )
        db.session.add(po)
        db.session.commit()
        get_vcs.return_value = self.get_fake_vcs()
        self.create_revision(
            repository=self.project.repository,
            sha='a' * 40
        )
        resp = self.client.post(self.path, data={
            'apply_project_files_trigger': '1',
            'sha': 'a' * 40,
            'repository': self.project.repository.url
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 0

    @patch('changes.models.Repository.get_vcs')
    def test_when_in_whitelist_commit_build(self, get_vcs):
        po = ProjectOption(
            project=self.project,
            name='build.file-whitelist',
            value='ci/*',
        )
        db.session.add(po)
        db.session.commit()
        get_vcs.return_value = self.get_fake_vcs()
        revision = self.create_revision(
            repository=self.project.repository,
            sha='a' * 40
        )
        resp = self.client.post(self.path, data={
            'apply_project_files_trigger': '1',
            'sha': 'a' * 40,
            'repository': self.project.repository.url
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id']

        job = Job.query.filter(
            Job.build_id == data[0]['id']
        ).first()
        build = job.build
        source = build.source

        assert job.project == self.project
        assert source.revision_sha == revision.sha

    @patch('changes.models.Repository.get_vcs')
    def test_when_in_whitelist_commit_build_default_false(self, get_vcs):
        po = ProjectOption(
            project=self.project,
            name='build.file-whitelist',
            value='nonexisting_directory',
        )
        db.session.add(po)
        db.session.commit()
        get_vcs.return_value = self.get_fake_vcs()
        revision = self.create_revision(
            repository=self.project.repository,
            sha='a' * 40
        )
        resp = self.client.post(self.path, data={
            'sha': 'a' * 40,
            'repository': self.project.repository.url
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id']

        job = Job.query.filter(
            Job.build_id == data[0]['id']
        ).first()
        build = job.build
        source = build.source

        assert job.project == self.project
        assert source.revision_sha == revision.sha

    @patch('changes.models.Repository.get_vcs')
    def test_when_in_whitelist_commit_build_false(self, get_vcs):
        po = ProjectOption(
            project=self.project,
            name='build.file-whitelist',
            value='nonexisting_directory',
        )
        db.session.add(po)
        db.session.commit()
        get_vcs.return_value = self.get_fake_vcs()
        revision = self.create_revision(
            repository=self.project.repository,
            sha='a' * 40
        )
        resp = self.client.post(self.path, data={
            'sha': 'a' * 40,
            'repository': self.project.repository.url,
            'apply_project_files_trigger': '',
            'ensure_only': '1',
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id']

        job = Job.query.filter(
            Job.build_id == data[0]['id']
        ).first()
        build = job.build
        source = build.source

        assert job.project == self.project
        assert source.revision_sha == revision.sha

    @patch('changes.models.Repository.get_vcs')
    def test_when_in_blacklist_commit_build(self, get_vcs):
        fake_vcs = self.get_fake_vcs()
        fake_vcs.read_file.side_effect = None
        fake_vcs.read_file.return_value = yaml.safe_dump({
            'build.file-blacklist': ['ci/*'],
        })
        get_vcs.return_value = fake_vcs
        self.create_revision(
            repository=self.project.repository,
            sha='a' * 40
        )
        resp = self.client.post(self.path, data={
            'apply_project_files_trigger': '1',
            'sha': 'a' * 40,
            'repository': self.project.repository.url
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 0

    @patch('changes.models.Repository.get_vcs')
    def test_when_not_all_in_blacklist_commit_build(self, get_vcs):
        fake_vcs = self.get_fake_vcs()
        fake_vcs.read_file.side_effect = None
        fake_vcs.read_file.return_value = yaml.safe_dump({
            'build.file-blacklist': ['ci/not-real'],
        })
        get_vcs.return_value = fake_vcs
        self.create_revision(
            repository=self.project.repository,
            sha='a' * 40
        )
        resp = self.client.post(self.path, data={
            'apply_project_files_trigger': '1',
            'sha': 'a' * 40,
            'repository': self.project.repository.url
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1

    @patch('changes.models.Repository.get_vcs')
    def test_when_in_blacklist_diff_build(self, get_vcs):
        fake_vcs = self.get_fake_vcs()
        fake_vcs.read_file.side_effect = None
        fake_vcs.read_file.return_value = yaml.safe_dump({
            'build.file-blacklist': ['ci/*'],
        })
        get_vcs.return_value = fake_vcs

        resp = self.post_sample_patch({
            'apply_project_files_trigger': '1',
        })
        assert resp.status_code == 200, resp.data
        data = self.unserialize(resp)
        assert len(data) == 0

    @patch('changes.models.Repository.get_vcs')
    def test_when_not_all_in_blacklist_diff_build(self, get_vcs):
        fake_vcs = self.get_fake_vcs()
        fake_vcs.read_file.side_effect = None
        fake_vcs.read_file.return_value = yaml.safe_dump({
            'build.file-blacklist': ['ci/not-real'],
        })
        get_vcs.return_value = fake_vcs

        resp = self.post_sample_patch({
            'apply_project_files_trigger': '1',
        })
        assert resp.status_code == 200, resp.data
        data = self.unserialize(resp)
        assert len(data) == 1

    @patch('changes.models.Repository.get_vcs')
    def test_when_not_all_in_blacklist_diff_build_invalid_diff(self, get_vcs):
        fake_vcs = self.get_fake_vcs()
        fake_vcs.read_file.side_effect = None
        fake_vcs.read_file.return_value = yaml.safe_dump({
            'build.file-blacklist': ['ci/*'],
        })
        get_vcs.return_value = fake_vcs

        with patch('changes.api.build_index.files_changed_should_trigger_project') as mocked:
            mocked.side_effect = InvalidDiffError
            resp = self.post_sample_patch({
                'apply_project_files_trigger': '1',
            })
        assert resp.status_code == 200, resp.data
        data = self.unserialize(resp)
        assert len(data) == 1

    @patch('changes.models.Repository.get_vcs')
    def test_when_not_all_in_blacklist_invalid_config(self, get_vcs):
        fake_vcs = self.get_fake_vcs()
        fake_vcs.read_file.side_effect = None
        fake_vcs.read_file.return_value = yaml.safe_dump({
            'build.file-blacklist': ['ci/*'],
        }) + '}'
        get_vcs.return_value = fake_vcs

        resp = self.client.post(self.path, data={
            'apply_project_files_trigger': '1',
            'sha': 'a' * 40,
            'repository': self.project.repository.url
        })
        assert resp.status_code == 200, resp.data
        data = self.unserialize(resp)
        assert len(data) == 1

    @patch('changes.models.Repository.get_vcs')
    def test_ensure_existing_build_complete(self, get_vcs):
        """Tests when all builds have already been created"""
        get_vcs.return_value = self.get_fake_vcs()
        revision = self.create_revision(
            repository=self.project.repository,
            sha='a' * 40
        )
        source = self.create_source(self.project, revision=revision)
        build = self.create_build(self.project, source=source)
        resp = self.client.post(self.path, data={
            'sha': 'a' * 40,
            'project': self.project.slug,
            'apply_project_files_trigger': '1',
            'ensure_only': '1',
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == build.id.hex

    @patch('changes.models.Repository.get_vcs')
    def test_ensure_existing_build_incomplete(self, get_vcs):
        """Tests when only a subset of the builds have been created"""
        project2 = self.create_project(repository=self.project.repository)
        self.create_plan(project2)
        db.session.commit()
        get_vcs.return_value = self.get_fake_vcs()
        revision = self.create_revision(
            repository=self.project.repository,
            sha='a' * 40
        )
        source = self.create_source(self.project, revision=revision)
        build = self.create_build(self.project, source=source)
        resp = self.client.post(self.path, data={
            'sha': 'a' * 40,
            'repository': self.project.repository.url,
            'apply_project_files_trigger': '1',
            'ensure_only': '1',
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 2
        assert len([x for x in data if x['id'] == build.id.hex]) == 1
        assert len(
            [x for x in data if x['project']['slug'] == self.project.slug]) == 1
        assert len(
            [x for x in data if x['project']['slug'] == project2.slug]) == 1

    @patch('changes.models.Repository.get_vcs')
    def test_ensure_multiple_existing_build(self, get_vcs):
        """Tests when only a subset of the builds have been created"""
        get_vcs.return_value = self.get_fake_vcs()
        revision = self.create_revision(
            repository=self.project.repository,
            sha='a' * 40
        )
        source = self.create_source(self.project, revision=revision)

        # this is older and won't be returned
        self.create_build(self.project, source=source)
        build = self.create_build(self.project, source=source)
        resp = self.client.post(self.path, data={
            'sha': 'a' * 40,
            'repository': self.project.repository.url,
            'apply_project_files_trigger': '1',
            'ensure_only': '1',
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == build.id.hex
        assert data[0]['project']['slug'] == self.project.slug

    @patch('changes.models.Repository.get_vcs')
    def test_ensure_existing_build_wrong_revision(self, get_vcs):
        """Tests when other builds in the system exist"""
        get_vcs.return_value = self.get_fake_vcs()
        wrong_revision = self.create_revision(
            repository=self.project.repository,
            sha='b' * 40
        )
        source = self.create_source(self.project, revision=wrong_revision)

        # this is older and won't be returned
        self.create_build(self.project, source=source)
        build = self.create_build(self.project, source=source)
        resp = self.client.post(self.path, data={
            'sha': 'a' * 40,
            'repository': self.project.repository.url,
            'apply_project_files_trigger': '1',
            'ensure_only': '1',
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] != build.id.hex

    @patch('changes.models.Repository.get_vcs')
    def test_ensure_existing_build_false(self, get_vcs):
        """Tests when existing builds have been created,
        but we don't want to run in ensure-only mode explicitly
        """
        get_vcs.return_value = self.get_fake_vcs()
        revision = self.create_revision(
            repository=self.project.repository,
            sha='a' * 40
        )
        source = self.create_source(self.project, revision=revision)
        build = self.create_build(self.project, source=source)
        resp = self.client.post(self.path, data={
            'sha': 'a' * 40,
            'project': self.project.slug,
            'apply_project_files_trigger': '1',
            'ensure_only': '',
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] != build.id.hex

    @patch('changes.models.Repository.get_vcs')
    def test_ensure_existing_build_default_false(self, get_vcs):
        """Tests when existing builds have been created,
        but we don't want to run in ensure-only mode by default
        """
        get_vcs.return_value = self.get_fake_vcs()
        revision = self.create_revision(
            repository=self.project.repository,
            sha='a' * 40
        )
        source = self.create_source(self.project, revision=revision)
        build = self.create_build(self.project, source=source)
        resp = self.client.post(self.path, data={
            'sha': 'a' * 40,
            'project': self.project.slug,
            'apply_project_files_trigger': '1',
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] != build.id.hex

    @patch('changes.models.Repository.get_vcs')
    def test_ensure_match_patch_want_commit(self, get_vcs):
        """This makes sure that the ensure API handles diff builds correctly.
        This is the case where we want to ensure a commit build.
        """
        get_vcs.return_value = self.get_fake_vcs()
        revision = self.create_revision(
            repository=self.project.repository,
            sha='a' * 40
        )
        patch = Patch(
            repository=self.project.repository,
            parent_revision_sha=revision.sha,
            diff=SAMPLE_DIFF,
        )
        source = self.create_source(self.project, revision=revision)
        bad_source = self.create_source(self.project, revision=revision, patch=patch)
        build = self.create_build(self.project, source=source)

        # if diff builds weren't handled properly, this build would be older
        # and would be returned
        self.create_build(self.project, source=bad_source)
        resp = self.client.post(self.path, data={
            'sha': 'a' * 40,
            'project': self.project.slug,
            'apply_project_files_trigger': '1',
            'ensure_only': '1',
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == build.id.hex

    def test_ensure_match_patch_want_diff_error(self):
        """This tests that ensure-only mode does not work with diff builds.
        """
        resp = self.client.post(self.path, data={
            'sha': 'a' * 40,
            'project': self.project.slug,
            'apply_project_files_trigger': '1',
            'ensure_only': '1',
            'patch': (StringIO(SAMPLE_DIFF_BYTES), 'foo.diff'),
            'target': 'D123',
        })
        assert resp.status_code == 400
        data = self.unserialize(resp)
        assert 'patch' in data['problems']
        assert 'ensure_only' in data['problems']

    @patch('changes.models.Repository.get_vcs')
    def test_existing_build_wrong_revision(self, get_vcs):
        """Tests when other builds in the system exist"""
        get_vcs.return_value = self.get_fake_vcs()
        revision = self.create_revision(
            repository=self.project.repository,
            sha='a' * 40
        )
        wrong_revision = self.create_revision(
            repository=self.project.repository,
            sha='b' * 40
        )
        source = self.create_source(self.project, revision=wrong_revision)

        # this is older and won't be returned
        self.create_build(self.project, source=source)
        build = self.create_build(self.project, source=source)
        resp = self.client.post(self.path, data={
            'sha': 'a' * 40,
            'repository': self.project.repository.url
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] != build.id.hex

    @patch('changes.models.Repository.get_vcs')
    def test_with_project_whitelist(self, get_vcs):
        project2 = self.create_project(repository=self.project.repository)
        self.create_plan(project2)
        db.session.commit()
        get_vcs.return_value = self.get_fake_vcs()
        self.create_revision(
            repository=self.project.repository,
            sha='a' * 40
        )
        resp = self.client.post(self.path, data={
            'sha': 'a' * 40,
            'repository': self.project.repository.url,
            'project_whitelist': json.dumps([project2.slug]),
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        job = Job.query.filter(
            Job.build_id == data[0]['id']
        ).first()
        build = job.build

        assert job.project == project2

    @patch('changes.models.Repository.get_vcs')
    def test_with_project_whitelist_empty(self, get_vcs):
        project2 = self.create_project(repository=self.project.repository)
        self.create_plan(project2)
        db.session.commit()
        get_vcs.return_value = self.get_fake_vcs()
        self.create_revision(
            repository=self.project.repository,
            sha='a' * 40
        )
        resp = self.client.post(self.path, data={
            'sha': 'a' * 40,
            'repository': self.project.repository.url,
            'project_whitelist': json.dumps([]),
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 0

    @patch('changes.models.Repository.get_vcs')
    @patch('changes.api.build_index.find_green_parent_sha')
    def test_with_full_params(self, mock_find_green_parent_sha, get_vcs):
        mock_find_green_parent_sha.return_value = 'b' * 40
        get_vcs.return_value = self.get_fake_vcs()

        resp = self.post_sample_patch()
        assert resp.status_code == 200, resp.data

        # TODO(dcramer): re-enable test when find_green_parent_sha is turned
        # back on
        # mock_find_green_parent_sha.assert_called_once_with(
        #     project=self.project,
        #     sha='a' * 40,
        # )

        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id']

        job = Job.query.filter(
            Job.build_id == data[0]['id']
        ).first()
        build = job.build
        source = build.source

        assert build.author.name == 'David Cramer'
        assert build.author.email == 'dcramer@example.com'
        assert build.message == 'Hello world!'
        assert build.label == 'Foo Bar'
        assert build.target == 'D1234'

        assert job.project == self.project
        assert job.label == self.plan.label

        assert source.repository_id == self.project.repository_id
        # TODO(dcramer): re-enable test when find_green_parent_sha is turned
        # assert source.revision_sha == 'b' * 40
        assert source.revision_sha == 'a' * 40
        assert source.data == {'foo': 'bar'}

        patch = source.patch
        assert patch.diff == SAMPLE_DIFF
        # we still reference the precise parent revision for patches
        assert patch.parent_revision_sha == 'a' * 40

        jobplans = list(JobPlan.query.filter(
            JobPlan.build_id == build.id,
        ))

        assert len(jobplans) == 1

        assert jobplans[0].job_id == job.id
        assert jobplans[0].plan_id == self.plan.id
        assert jobplans[0].project_id == self.project.id

    def _post_for_repo(self, repo):
        return self.client.post(self.path, data={
            'repository': repo.url,
            'sha': 'a' * 40,
        })

    def test_with_repository(self):
        repo = self.create_repo_with_projects(count=2)
        resp = self._post_for_repo(repo)
        self.assert_resp_has_multiple_items(resp, count=2)

    def test_collection_id(self):
        repo = self.create_repo_with_projects(count=3)
        resp = self._post_for_repo(repo)
        builds = self.assert_resp_has_multiple_items(resp, count=3)
        self.assert_collection_id_across_builds(builds)

    def test_with_repository_callsign(self):
        repo = self.create_repo_with_projects(count=2)
        self.create_option(
            item_id=repo.id,
            name='phabricator.callsign',
            value='FOO',
        )
        db.session.commit()

        resp = self.client.post(self.path, data={
            'repository[phabricator.callsign]': 'FOO',
            'sha': 'a' * 40,
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 2

    @patch('changes.models.Repository.get_vcs')
    def test_with_empty_changeset(self, get_vcs):
        get_vcs.return_value = self.get_fake_vcs()

        resp = self.client.post(self.path, data={
            'apply_project_files_trigger': '1',
            'project': self.project.slug,
            'sha': 'a' * 40,
            'target': 'D1234',
            'label': 'Foo Bar',
            'message': 'Hello world!',
            'author': 'David Cramer <dcramer@example.com>',
            'patch': (StringIO(""), 'foo.diff'),
            'patch[data]': '{"foo": "bar"}'
        })
        assert resp.status_code == 200, resp.data
        data = self.unserialize(resp)
        assert len(data) == 0

    def test_no_project_and_no_repo(self):
        resp = self.client.post(self.path, data={
            'apply_project_files_trigger': '1',
            'sha': 'a' * 40,
            'target': 'D1234',
            'label': 'Foo Bar',
            'message': 'Hello world!',
            'author': 'David Cramer <dcramer@example.com>',
            'patch': (StringIO(""), 'foo.diff'),
            'patch[data]': '{"foo": "bar"}'
        })
        assert resp.status_code == 400

        data = self.unserialize(resp)
        assert "project" in data['problems']
        assert "repository" in data['problems']
        assert "repository[phabricator.callsign]" in data['problems']

    def test_patch_data_is_not_json(self):
        resp = self.client.post(self.path, data={
            'apply_project_files_trigger': '1',
            'project': self.project.slug,
            'sha': 'a' * 40,
            'target': 'D1234',
            'label': 'Foo Bar',
            'message': 'Hello world!',
            'author': 'David Cramer <dcramer@example.com>',
            'patch': (StringIO(""), 'foo.diff'),
            'patch[data]': '{"foo": "bar"'
        })
        assert resp.status_code == 400

        data = self.unserialize(resp)
        assert "patch[data]" in data['problems']

    def test_patch_data_is_non_dict_json(self):
        resp = self.client.post(self.path, data={
            'apply_project_files_trigger': '1',
            'project': self.project.slug,
            'sha': 'a' * 40,
            'target': 'D1234',
            'label': 'Foo Bar',
            'message': 'Hello world!',
            'author': 'David Cramer <dcramer@example.com>',
            'patch': (StringIO(""), 'foo.diff'),
            'patch[data]': '["foo", "bar"]'
        })
        assert resp.status_code == 400

        data = self.unserialize(resp)
        assert "patch[data]" in data['problems']
