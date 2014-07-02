from changes.config import db
from changes.models import ProjectOption
from changes.testutils import APITestCase


class ProjectOptionsTest(APITestCase):
    def test_simple(self):
        project = self.create_project()
        path = '/api/0/projects/{0}/options/'.format(project.slug)

        resp = self.client.post(path, data={
            'mail.notify-author': '0',
            'build.allow-patches': '1',
            'build.expect-tests': '1',
        })
        assert resp.status_code == 401

        self.login_default()

        resp = self.client.post(path, data={
            'mail.notify-author': '0',
            'build.allow-patches': '1',
            'build.expect-tests': '1',
        })
        assert resp.status_code == 200

        options = dict(db.session.query(
            ProjectOption.name, ProjectOption.value
        ).filter(
            ProjectOption.project == project,
        ))

        assert options.get('mail.notify-author') == '0'
        assert options.get('build.allow-patches') == '1'
        assert options.get('build.expect-tests') == '1'
