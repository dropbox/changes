from changes.models import ProjectOption
from changes.testutils import APITestCase


class BuildListTest(APITestCase):
    def test_simple(self):
        path = '/api/0/projects/{0}/options/'.format(self.project.slug)

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
        assert resp.status_code == 200

        option = ProjectOption.query.filter(
            ProjectOption.project == self.project,
            ProjectOption.name == 'mail.notify-author',
        ).first()

        assert option.value == '0'

        option = ProjectOption.query.filter(
            ProjectOption.project == self.project,
            ProjectOption.name == 'build.allow-patches',
        ).first()

        assert option.value == '1'
