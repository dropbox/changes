from changes.testutils import APITestCase

import datetime
import mock


class CachedSnapshotClusterDetailsAPITestCase(APITestCase):
    def setUp(self):
        super(CachedSnapshotClusterDetailsAPITestCase, self).setUp()
        self.mock_datetime = datetime.datetime.utcnow()

    def get_endpoint_path(self, cluster):
        return '/api/0/snapshots/cache/clusters/{0}/'.format(cluster)

    def test_empty(self):
        resp = self.client.get(self.get_endpoint_path('cluster'))
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data == []

    @mock.patch('changes.lib.snapshot_garbage_collection.get_current_datetime')
    def test_get_current_datetime(self, get_current_datetime):
        """Metatest that verifies that the time-mock is functional.
        """
        get_current_datetime.return_value = self.mock_datetime
        self.client.get(self.get_endpoint_path('cluster'))
        get_current_datetime.assert_any_call()

    @mock.patch('changes.lib.snapshot_garbage_collection.get_current_datetime')
    def test_multiproject(self, get_current_datetime):
        """
        Integration test (minus mocking out time) on the endpoint, which is
        different from the lib-tests which mock out get_plans in the garbage
        collector.
        """
        project1 = self.create_project()
        project2 = self.create_project()
        plan1_1 = self.create_plan(project1)
        plan1_2 = self.create_plan(project1)
        plan2_1 = self.create_plan(project2)
        plan2_2 = self.create_plan(project2)
        plan2_3 = self.create_plan(project2)

        self.create_step(plan1_1, data={'cluster': 'cluster1'})
        self.create_step(plan1_2, data={'cluster': 'cluster2'})
        self.create_step(plan2_1, data={'cluster': 'cluster2'})
        self.create_step(plan2_2, data={'cluster': 'cluster2'})

        snapshot1 = self.create_snapshot(project1)
        snapshot2 = self.create_snapshot(project2)
        snapshot_image1_1 = self.create_snapshot_image(snapshot1, plan1_1)
        snapshot_image1_2 = self.create_snapshot_image(snapshot1, plan1_2)
        snapshot_image2_1 = self.create_snapshot_image(snapshot2, plan2_1)
        snapshot_image2_2 = self.create_snapshot_image(snapshot2, plan2_2)
        snapshot_image2_3 = self.create_snapshot_image(snapshot2, plan2_3)

        self.create_cached_snapshot_image(snapshot_image1_1)
        self.create_cached_snapshot_image(snapshot_image1_2,
            expiration_date=self.mock_datetime + datetime.timedelta(0, 1))
        self.create_cached_snapshot_image(snapshot_image2_1,
            expiration_date=self.mock_datetime - datetime.timedelta(0, 1))
        self.create_cached_snapshot_image(snapshot_image2_2)
        self.create_cached_snapshot_image(snapshot_image2_3)

        get_current_datetime.return_value = self.mock_datetime

        resp = self.client.get(self.get_endpoint_path('cluster2'))
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 2
        assert snapshot_image1_2.id.hex in data
        assert snapshot_image2_2.id.hex in data

        # Ensure that nonexisting clusters still give empty even when there
        # is actually some data (unlike test_empty)
        resp = self.client.get(self.get_endpoint_path('cluster3'))
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data == []
