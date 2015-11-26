from changes.testutils import APITestCase


class JenkinsMasterBlacklist(APITestCase):
    def test_add_remove_blacklist(self):
        path = '/api/0/jenkins_master_blacklist/'

        # Add to blacklist
        data = dict(master_url='https://jenkins-master-a')
        resp = self.client.post(path, data=data)
        assert resp.status_code == 200
        data = dict(master_url='https://jenkins-master-b')
        resp = self.client.post(path, data=data)
        assert resp.status_code == 200

        resp = self.client.get(path)
        resp.status_code == 200
        result = self.unserialize(resp)
        assert 'https://jenkins-master-a' in result['blacklist']
        assert 'https://jenkins-master-b' in result['blacklist']

        # Delete from blacklist
        data = dict(master_url='https://jenkins-master-a', remove=1)
        resp = self.client.post(path, data=data)
        resp.status_code == 200
        assert ['https://jenkins-master-b'] == self.unserialize(resp)['blacklist']

    def test_re_add(self):
        path = '/api/0/jenkins_master_blacklist/'
        data = dict(master_url='https://jenkins-master-a')
        resp = self.client.post(path, data=data)
        assert resp.status_code == 200
        data = dict(master_url='https://jenkins-master-a')
        resp = self.client.post(path, data=data)
        assert resp.status_code == 200
        result = self.unserialize(resp)
        assert 'warning' in result

    def test_remove_missing(self):
        path = '/api/0/jenkins_master_blacklist/'
        data = dict(master_url='https://jenkins-master-a', remove=1)
        resp = self.client.post(path, data=data)
        assert resp.status_code == 200
        result = self.unserialize(resp)
        assert 'warning' in result
