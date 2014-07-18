from changes.config import db
from changes.models import ProjectOption, SnapshotStatus
from changes.testutils import APITestCase


class ProjectOptionsTest(APITestCase):
    def test_simple(self):
        project = self.create_project()
        path = '/api/0/projects/{0}/options/'.format(project.slug)

        resp = self.client.post(path, data={
            'mail.notify-author': '0',
            'build.allow-patches': '1',
        })
        assert resp.status_code == 401

        self.login_default()

        resp = self.client.post(path, data={
            'mail.notify-author': '0',
            'build.allow-patches': '1',
        })
        assert resp.status_code == 403

        self.login_default_admin()

        resp = self.client.post(path, data={
            'mail.notify-author': '0',
            'build.allow-patches': '1',
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
        assert options.get('build.allow-patches') == '1'
        assert options.get('snapshot.current') == snapshot.id.hex
