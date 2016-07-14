from __future__ import absolute_import, division, unicode_literals

import yaml

from cStringIO import StringIO
from datetime import datetime
from mock import ANY, Mock, patch

from changes.config import db
from changes.models.job import Job
from changes.models.jobplan import JobPlan
from changes.models.project import ProjectOption
from changes.testutils import APITestCase, SAMPLE_DIFF, SAMPLE_DIFF_BYTES
from changes.testutils.build import CreateBuildsMixin
from changes.vcs.base import CommandError, RevisionResult, Vcs, UnknownRevision

_VALID_SHA = 'a' * 40
_BOGUS_SHA = 'b' * 40


class PhabricatorNotifyDiffTest(APITestCase, CreateBuildsMixin):
    path = '/api/0/phabricator/notify-diff/'

    def get_fake_vcs(self, log_results=None):
        def _log_results(parent=None, branch=None, offset=0, limit=1):
            assert not branch
            if parent not in (None, _VALID_SHA):
                raise CommandError(cmd="test command", retcode=128)
            return iter([
                RevisionResult(
                    id=_VALID_SHA,
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
        fake_vcs.get_patch_hash.return_value = 'a' * 40

        def fake_update():
            # this simulates the effect of calling update() on a repo,
            # mainly that `export` and `log` now works.
            fake_vcs.log.side_effect = log_results
            fake_vcs.export.side_effect = None
            fake_vcs.export.return_value = SAMPLE_DIFF_BYTES

        fake_vcs.update.side_effect = fake_update

        return fake_vcs

    def post_sample_patch(self):
        return self.client.post(self.path, data={
            'phabricator.callsign': 'FOO',
            'phabricator.diffID': '1324134',
            'phabricator.revisionID': '1234',
            'phabricator.revisionURL': 'https://phabricator.example.com/D1234',
            'patch': (StringIO(SAMPLE_DIFF_BYTES), 'foo.diff'),
            'sha': _VALID_SHA,
            'label': 'Foo Bar',
            'message': 'Hello world!',
            'author': 'David Cramer <dcramer@example.com>',
        })

    @patch('changes.models.repository.Repository.get_vcs')
    def test_valid_params(self, get_vcs):
        get_vcs.return_value = self.get_fake_vcs()
        repo = self.create_repo()

        project = self.create_project(repository=repo)
        plan = self.create_plan(project)
        self.create_option(
            item_id=repo.id,
            name='phabricator.callsign',
            value='FOO',
        )
        db.session.commit()

        resp = self.post_sample_patch()
        assert resp.status_code == 200
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

        assert job.project == project
        assert job.label == plan.label

        assert source.repository_id == project.repository_id
        # TODO(dcramer): re-enable test when find_green_parent_sha is turned
        # assert source.revision_sha == 'b' * 40
        assert source.revision_sha == _VALID_SHA
        assert source.data == {
            'phabricator.buildTargetPHID': None,
            'phabricator.diffID': '1324134',
            'phabricator.revisionID': '1234',
            'phabricator.revisionURL': 'https://phabricator.example.com/D1234',
        }

        patch = source.patch
        assert patch.diff == SAMPLE_DIFF
        # we still reference the precise parent revision for patches
        assert patch.parent_revision_sha == _VALID_SHA

        jobplans = list(JobPlan.query.filter(
            JobPlan.build_id == build.id,
        ))

        assert len(jobplans) == 1

        assert jobplans[0].job_id == job.id
        assert jobplans[0].plan_id == plan.id
        assert jobplans[0].project_id == project.id

    def test_with_patch_without_diffs_enabled(self):
        repo = self.create_repo()

        project = self.create_project(repository=repo)
        self.create_plan(project)
        self.create_option(
            item_id=repo.id,
            name='phabricator.callsign',
            value='FOO',
        )

        po = ProjectOption(
            project=project,
            name='phabricator.diff-trigger',
            value='0',
        )
        db.session.add(po)
        db.session.commit()

        # Default to not creating a build (for tools)
        resp = self.post_sample_patch()
        assert resp.status_code == 200, resp.data
        data = self.unserialize(resp)
        assert len(data) == 0

    @patch('changes.models.repository.Repository.get_vcs')
    def test_when_not_in_whitelist(self, get_vcs):
        get_vcs.return_value = self.get_fake_vcs()
        repo = self.create_repo()

        project = self.create_project(repository=repo)
        self.create_plan(project)
        self.create_option(
            item_id=repo.id,
            name='phabricator.callsign',
            value='FOO',
        )

        po = ProjectOption(
            project=project,
            name='build.file-whitelist',
            value='nonexisting_directory',
        )
        db.session.add(po)
        db.session.commit()

        resp = self.post_sample_patch()
        assert resp.status_code == 200, resp.data
        data = self.unserialize(resp)
        assert len(data) == 0

    @patch('changes.models.repository.Repository.get_vcs')
    def test_when_in_whitelist(self, get_vcs):
        get_vcs.return_value = self.get_fake_vcs()
        repo = self.create_repo()

        project = self.create_project(repository=repo)
        self.create_plan(project)
        self.create_option(
            item_id=repo.id,
            name='phabricator.callsign',
            value='FOO',
        )

        po = ProjectOption(
            project=project,
            name='build.file-whitelist',
            value='ci/*',
        )
        db.session.add(po)
        db.session.commit()

        resp = self.post_sample_patch()
        assert resp.status_code == 200, resp.data
        data = self.unserialize(resp)
        assert len(data) == 1

    @patch('changes.models.repository.Repository.get_vcs')
    def test_when_in_blacklist(self, get_vcs):
        fake_vcs = self.get_fake_vcs()
        fake_vcs.read_file.side_effect = None
        fake_vcs.read_file.return_value = yaml.safe_dump({
            'build.file-blacklist': ['ci/*'],
        })
        get_vcs.return_value = fake_vcs
        repo = self.create_repo()
        self.create_option(
            item_id=repo.id,
            name='phabricator.callsign',
            value='FOO',
        )

        project = self.create_project(repository=repo)
        self.create_plan(project)

        resp = self.post_sample_patch()
        assert resp.status_code == 200, resp.data
        data = self.unserialize(resp)
        assert len(data) == 0

    @patch('changes.models.repository.Repository.get_vcs')
    def test_when_not_all_in_blacklist(self, get_vcs):
        fake_vcs = self.get_fake_vcs()
        fake_vcs.read_file.side_effect = None
        fake_vcs.read_file.return_value = yaml.safe_dump({
            'build.file-blacklist': ['ci/not-real'],
        })
        get_vcs.return_value = fake_vcs
        repo = self.create_repo()
        self.create_option(
            item_id=repo.id,
            name='phabricator.callsign',
            value='FOO',
        )

        project = self.create_project(repository=repo)
        self.create_plan(project)

        resp = self.post_sample_patch()
        assert resp.status_code == 200, resp.data
        data = self.unserialize(resp)
        assert len(data) == 1

    @patch('changes.models.repository.Repository.get_vcs')
    def test_invalid_config(self, get_vcs):
        fake_vcs = self.get_fake_vcs()
        fake_vcs.read_file.side_effect = None
        fake_vcs.read_file.return_value = yaml.safe_dump({
            'build.file-blacklist': ['ci/*'],
        }) + '}'
        get_vcs.return_value = fake_vcs
        repo = self.create_repo()
        self.create_option(
            item_id=repo.id,
            name='phabricator.callsign',
            value='FOO',
        )

        project = self.create_project(repository=repo)
        self.create_plan(project)

        resp = self.post_sample_patch()
        assert resp.status_code == 200, resp.data
        data = self.unserialize(resp)
        assert len(data) == 1

    @patch('changes.models.repository.Repository.get_vcs')
    def test_collection_id(self, get_vcs):
        get_vcs.return_value = self.get_fake_vcs()
        repo = self.create_repo_with_projects(count=3)
        self.create_option(
            item_id=repo.id,
            name='phabricator.callsign',
            value='FOO',
        )
        db.session.commit()
        resp = self.post_sample_patch()
        builds = self.assert_resp_has_multiple_items(resp, count=3)
        self.assert_collection_id_across_builds(builds)

    @patch('changes.models.repository.Repository.get_vcs')
    @patch('changes.api.phabricator_notify_diff.post_comment')
    def test_diff_comment(self, mock_post_comment, get_vcs):
        """Test diff commenting on a revision we can't identify on a legit project"""
        get_vcs.return_value = self.get_fake_vcs()
        repo = self.create_repo()
        self.create_option(
            item_id=repo.id,
            name='phabricator.callsign',
            value='FOO',
        )
        project = self.create_project(repository=repo)
        self.create_plan(project)

        # Test that valid sha doesn't kick off anything
        resp = self.client.post(self.path, data={
            'phabricator.callsign': 'FOO',
            'phabricator.diffID': '1324134',
            'phabricator.revisionID': '1234',
            'phabricator.revisionURL': 'https://phabricator.example.com/D1234',
            'patch': (StringIO(SAMPLE_DIFF_BYTES), 'foo.diff'),
            'sha': _VALID_SHA,
            'label': 'Foo Bar',
            'message': 'Hello world!',
            'author': 'David Cramer <dcramer@example.com>'
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert mock_post_comment.call_count == 0

        # Test that invalid sha kicks off a mock comment
        resp = self.client.post(self.path, data={
            'phabricator.callsign': 'FOO',
            'phabricator.diffID': '1324134',
            'phabricator.revisionID': '1234',
            'phabricator.revisionURL': 'https://phabricator.example.com/D1234',
            'patch': (StringIO(SAMPLE_DIFF_BYTES), 'foo.diff'),
            'sha': _BOGUS_SHA,
            'label': 'Foo Bar',
            'message': 'Hello world!',
            'author': 'David Cramer <dcramer@example.com>'
        })
        assert resp.status_code == 400
        data = self.unserialize(resp)
        assert "Unable to find base revision %s" % _BOGUS_SHA in data['error']
        mock_post_comment.assert_called_once_with('D1234', ANY)
        assert "An error occurred somewhere between Phabricator and Changes" in mock_post_comment.call_args[0][1]
        assert "Unable to find base revision %s" % _BOGUS_SHA in mock_post_comment.call_args[0][1]

    @patch('changes.models.repository.Repository.get_vcs')
    @patch('changes.api.phabricator_notify_diff.post_comment')
    def test_diff_comment_bad_project(self, mock_post_comment, get_vcs):
        """Make sure we don't comment on diffs for repos without projects/plans"""
        get_vcs.return_value = self.get_fake_vcs()
        repo = self.create_repo()
        self.create_option(
            item_id=repo.id,
            name='phabricator.callsign',
            value='FOO',
        )

        # There's no project for this repo. Don't post back comments.
        resp = self.client.post(self.path, data={
            'phabricator.callsign': 'FOO',
            'phabricator.diffID': '1324134',
            'phabricator.revisionID': '1234',
            'phabricator.revisionURL': 'https://phabricator.example.com/D1234',
            'patch': (StringIO(SAMPLE_DIFF_BYTES), 'foo.diff'),
            'sha': _BOGUS_SHA,
            'label': 'Foo Bar',
            'message': 'Hello world!',
            'author': 'David Cramer <dcramer@example.com>'
        })
        assert resp.status_code == 200
        assert self.unserialize(resp) == []
        assert mock_post_comment.call_count == 0

        # Now with a project, but no build plans. Don't post back comments
        project = self.create_project(repository=repo)
        resp = self.client.post(self.path, data={
            'phabricator.callsign': 'FOO',
            'phabricator.diffID': '1324134',
            'phabricator.revisionID': '1234',
            'phabricator.revisionURL': 'https://phabricator.example.com/D1234',
            'patch': (StringIO(SAMPLE_DIFF_BYTES), 'foo.diff'),
            'sha': _BOGUS_SHA,
            'label': 'Foo Bar',
            'message': 'Hello world!',
            'author': 'David Cramer <dcramer@example.com>'
        })
        assert resp.status_code == 200
        assert self.unserialize(resp) == []
        assert mock_post_comment.call_count == 0

        # Now with a project and a plan, kick off comment
        self.create_plan(project)
        resp = self.client.post(self.path, data={
            'phabricator.callsign': 'FOO',
            'phabricator.diffID': '1324134',
            'phabricator.revisionID': '1234',
            'phabricator.revisionURL': 'https://phabricator.example.com/D1234',
            'patch': (StringIO(SAMPLE_DIFF_BYTES), 'foo.diff'),
            'sha': _BOGUS_SHA,
            'label': 'Foo Bar',
            'message': 'Hello world!',
            'author': 'David Cramer <dcramer@example.com>'
        })
        assert resp.status_code == 400
        data = self.unserialize(resp)
        assert "Unable to find base revision %s" % _BOGUS_SHA in data['error']
        mock_post_comment.assert_called_once_with('D1234', ANY)
        assert "An error occurred somewhere between Phabricator and Changes" in mock_post_comment.call_args[0][1]
        assert "Unable to find base revision %s" % _BOGUS_SHA in mock_post_comment.call_args[0][1]
