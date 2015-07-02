from changes.testutils import APITestCase

import datetime
import mock


class CachedSnapshotClusterDetailsAPITestCase(APITestCase):
    def setUp(self):
        super(CachedSnapshotClusterDetailsAPITestCase, self).setUp()
        self.mock_datetime = datetime.datetime.utcnow()

    def get_endpoint_path(self, snapshot_id):
        return '/api/0/snapshots/{0}/cache/'.format(snapshot_id.hex)

    def test_nonexistant_snapshot(self):
        project = self.create_project()
        resp = self.client.post(self.get_endpoint_path(project.id))
        assert resp.status_code == 404

    def test_snapshot_without_images(self):
        project = self.create_project()
        snapshot = self.create_snapshot(project)
        resp = self.client.post(self.get_endpoint_path(snapshot.id))
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data == {}

    def test_simple(self):
        """
        Test with a project with only one plan and no pre-existing
        snapshots/cached snapshots, the simplest possible case.
        """
        project = self.create_project()
        plan = self.create_plan(project)
        self.create_step(plan, data={'cluster': 'cluster'})
        snapshot = self.create_snapshot(project)
        snapshot_image = self.create_snapshot_image(snapshot, plan)

        resp = self.client.post(self.get_endpoint_path(snapshot.id))
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data == {'cluster': [snapshot_image.id.hex]}

    @mock.patch('changes.lib.snapshot_garbage_collection.get_current_datetime')
    def test_expire(self, get_current_datetime):
        """
        Test expiring a cached snapshot by caching a snapshot with the
        same project.
        """
        project = self.create_project()
        plan = self.create_plan(project)
        self.create_step(plan, data={'cluster': 'cluster'})
        old_snapshot = self.create_snapshot(project)
        old_snapshot_image = self.create_snapshot_image(old_snapshot, plan)
        self.create_cached_snapshot_image(old_snapshot_image)

        snapshot = self.create_snapshot(project)
        snapshot_image = self.create_snapshot_image(snapshot, plan)

        get_current_datetime.return_value = self.mock_datetime

        resp = self.client.post(self.get_endpoint_path(snapshot.id))
        assert resp.status_code == 200
        data = self.unserialize(resp)

        assert len(data) == 1
        assert 'cluster' in data
        assert len(data['cluster']) == 2
        assert snapshot_image.id.hex in data['cluster']

        # The old one hasn't expired quite yet so it should still
        # be in the sync information
        assert old_snapshot_image.id.hex in data['cluster']

    @mock.patch('changes.lib.snapshot_garbage_collection.get_current_datetime')
    def test_multiproject(self, get_current_datetime):
        """
        Test the scenario when the cluster that updated also runs another project,
        which has existing cached snapshot images of that cluster.
        """
        project1 = self.create_project()
        project2 = self.create_project()
        plan1_1 = self.create_plan(project1)
        plan1_2 = self.create_plan(project1)
        plan1_3 = self.create_plan(project1)
        plan2_1 = self.create_plan(project2)
        plan2_2 = self.create_plan(project2)

        self.create_step(plan1_1, data={'cluster': 'cluster1'})
        self.create_step(plan1_2, data={'cluster': 'cluster2'})
        self.create_step(plan2_1, data={'cluster': 'cluster2'})
        self.create_step(plan2_2, data={'cluster': 'cluster3'})

        snapshot1 = self.create_snapshot(project1)
        snapshot2 = self.create_snapshot(project2)
        snapshot_image1_1 = self.create_snapshot_image(snapshot1, plan1_1)
        snapshot_image1_2 = self.create_snapshot_image(snapshot1, plan1_2)
        snapshot_image1_3 = self.create_snapshot_image(snapshot1, plan1_3)
        snapshot_image2_1 = self.create_snapshot_image(snapshot2, plan2_1)
        snapshot_image2_2 = self.create_snapshot_image(snapshot2, plan2_2)

        self.create_cached_snapshot_image(snapshot_image2_1)
        self.create_cached_snapshot_image(snapshot_image2_2)

        get_current_datetime.return_value = self.mock_datetime

        resp = self.client.post(self.get_endpoint_path(snapshot1.id))
        assert resp.status_code == 200
        data = self.unserialize(resp)

        assert len(data) == 2
        assert 'cluster1' in data
        assert 'cluster2' in data
        assert len(data['cluster1']) == 1
        assert snapshot_image1_1.id.hex in data['cluster1']
        assert len(data['cluster2']) == 2
        assert snapshot_image1_2.id.hex in data['cluster2']
        assert snapshot_image2_1.id.hex in data['cluster2']
