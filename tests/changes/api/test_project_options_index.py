from datetime import datetime, timedelta
from mock import patch

from changes.config import db
from changes.models import ProjectOption, SnapshotStatus
from changes.testutils import APITestCase


class ProjectOptionsTest(APITestCase):
    def test_simple(self):
        project = self.create_project()
        path = '/api/0/projects/{0}/options/'.format(project.slug)

        resp = self.client.post(path, data={
            'mail.notify-author': '0',
            'phabricator.diff-trigger': '1',
        })
        assert resp.status_code == 401

        self.login_default()

        resp = self.client.post(path, data={
            'mail.notify-author': '0',
            'phabricator.diff-trigger': '1',
        })
        assert resp.status_code == 403

        self.login_default_admin()

        resp = self.client.post(path, data={
            'mail.notify-author': '0',
            'phabricator.diff-trigger': '1',
        })
        assert resp.status_code == 200

        # Test snapshot options
        snapshot = self.create_snapshot(project, status=SnapshotStatus.failed)
        resp = self.client.post(path, data={
            'snapshot.current': snapshot.id.hex,
        })

        assert resp.status_code == 400
        snapshot = self.create_snapshot(project, status=SnapshotStatus.active)
        resp = self.client.post(path, data={
            'snapshot.current': snapshot.id.hex,
        })
        assert resp.status_code == 200

        resp = self.client.post(path, data={
            'snapshot.current': "invalid id",
        })
        assert resp.status_code == 400

        options = dict(db.session.query(
            ProjectOption.name, ProjectOption.value
        ).filter(
            ProjectOption.project == project,
        ))

        assert options.get('mail.notify-author') == '0'
        assert options.get('phabricator.diff-trigger') == '1'
        assert options.get('snapshot.current') == snapshot.id.hex

    def test_nonsense_project(self):
        project = self.create_project()
        path_fmt = '/api/0/projects/{0}/options/'
        self.login_default_admin()
        resp = self.client.post(path_fmt.format('project-that-doesnt-exist'), data={
            'mail.notify-author': '0',
        })
        assert resp.status_code == 404

        # Random UUID.
        uuid_resp = self.client.post(path_fmt.format('fc0e5c51-19c5-43f0-9e11-8c28e091e9b0'), data={
            'mail.notify-author': '0',
        })
        assert uuid_resp.status_code == 404

    def test_report_rollback(self):
        project = self.create_project()
        path = '/api/0/projects/{0}/options/'.format(project.slug)
        self.login_default_admin()

        now = datetime(2013, 9, 19, 22, 15, 22)
        earlier = now - timedelta(days=1)

        older = self.create_snapshot(project, status=SnapshotStatus.active, date_created=earlier)

        snapshot = self.create_snapshot(project, status=SnapshotStatus.active, date_created=now)

        # To avoid duplication and as an offering to the line-length gods.
        PATCH_PATH = 'changes.api.project_options_index._report_snapshot_downgrade'
        with patch(PATCH_PATH) as report_downgrade:
            resp = self.client.post(path, data={
                'snapshot.current': snapshot.id.hex,
            })
            assert resp.status_code == 200
            assert not report_downgrade.called

        with patch(PATCH_PATH) as report_downgrade:
            resp = self.client.post(path, data={
                'snapshot.current': older.id.hex,
            })
            assert resp.status_code == 200
            report_downgrade.assert_called_once_with(project)

        # Deactivation without replacement.
        with patch(PATCH_PATH) as report_downgrade:
            resp = self.client.post(path, data={
                'snapshot.current': '',
            })
            assert resp.status_code == 200
            report_downgrade.assert_called_once_with(project)
