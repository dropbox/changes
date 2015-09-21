from changes.config import db
from changes.testutils.cases import TestCase
from changes.models import CachedSnapshotImage, PlanStatus
import changes.lib.snapshot_garbage_collection as gc

import datetime
import mock
import sqlalchemy


class TestSnapshotGCTestCase(TestCase):
    def setUp(self):
        """
        Used to fix the current time from datetime for the entirety of a
        single test.
        """
        self.mock_datetime = datetime.datetime.utcnow()
        super(TestSnapshotGCTestCase, self).setUp()

    def test_get_plans_for_cluster(self):
        project1 = self.create_project()
        project2 = self.create_project()
        plan1_1 = self.create_plan(project1)
        plan1_2 = self.create_plan(project1)
        plan2_1 = self.create_plan(project2)
        plan2_2 = self.create_plan(project2)
        plan2_3 = self.create_plan(project2)

        self.create_step(plan1_1, data={'cluster': 'cluster1'})
        self.create_step(plan1_2, data={'cluster': 'cluster2'})
        self.create_step(plan2_1, data={'cluster': 'cluster1'})

        # Inactive plan
        self.create_step(plan2_3, data={'cluster': 'cluster1'})
        plan2_3.status = PlanStatus.inactive
        db.session.commit()

        plans = gc.get_plans_for_cluster('cluster1')
        assert len(plans) == 2
        assert plan1_1 in plans
        assert plan2_1 in plans

    @mock.patch('changes.lib.snapshot_garbage_collection.get_plans_for_cluster')
    def test_cached_snapshot_images_gets_plans(self, get_plans):
        """More or less a metatest that verifies that the mocking
        is actually working.
        """
        project = self.create_project()
        plan = self.create_plan(project)
        snapshot = self.create_snapshot(project)

        snapshot_image = self.create_snapshot_image(snapshot, plan)
        cached_snapshot_image = self.create_cached_snapshot_image(snapshot_image)

        get_plans.return_value = set()
        gc.get_cached_snapshot_images('cluster')
        get_plans.assert_called_with('cluster')

    @mock.patch('changes.lib.snapshot_garbage_collection.get_plans_for_cluster')
    def test_cached_snapshot_images_no_plans(self, get_plans):
        project = self.create_project()
        plan = self.create_plan(project)
        snapshot = self.create_snapshot(project)

        snapshot_image = self.create_snapshot_image(snapshot, plan)
        cached_snapshot_image = self.create_cached_snapshot_image(snapshot_image)

        get_plans.return_value = set()

        assert gc.get_cached_snapshot_images('cluster') == []

    @mock.patch('changes.lib.snapshot_garbage_collection.get_current_datetime')
    @mock.patch('changes.lib.snapshot_garbage_collection.get_plans_for_cluster')
    def test_cached_snapshot_images_get_current_datetime(self, get_plans, get_current_datetime):
        """More or less a metatest that verifies that the mocking
        is actually working.
        """
        project = self.create_project()
        plan = self.create_plan(project)
        snapshot = self.create_snapshot(project)

        snapshot_image = self.create_snapshot_image(snapshot, plan)
        cached_snapshot_image = self.create_cached_snapshot_image(snapshot_image)

        get_plans.return_value = set()
        get_current_datetime.return_value = self.mock_datetime
        gc.get_cached_snapshot_images('cluster')
        get_current_datetime.assert_any_call()

    @mock.patch('changes.lib.snapshot_garbage_collection.get_current_datetime')
    @mock.patch('changes.lib.snapshot_garbage_collection.get_plans_for_cluster')
    def test_cached_snapshot_images_all(self, get_plans, get_current_datetime):
        """
        Tests the four fundamental cases for an image:
         - No expiration date
         - Not yet expired
         - Expired
         - Not part of the plans associated with the cluster
        """
        project = self.create_project()
        plan1 = self.create_plan(project)
        plan2 = self.create_plan(project)
        plan3 = self.create_plan(project)
        plan4 = self.create_plan(project)

        get_current_datetime.return_value = self.mock_datetime
        get_plans.return_value = {plan1, plan2, plan3}

        snapshot = self.create_snapshot(project)
        snapshot_image1 = self.create_snapshot_image(snapshot, plan1)
        snapshot_image2 = self.create_snapshot_image(snapshot, plan2)
        snapshot_image3 = self.create_snapshot_image(snapshot, plan3)
        snapshot_image4 = self.create_snapshot_image(snapshot, plan4)

        self.create_cached_snapshot_image(snapshot_image1, expiration_date=None)
        self.create_cached_snapshot_image(snapshot_image2,
                expiration_date=self.mock_datetime + datetime.timedelta(0, 1))
        self.create_cached_snapshot_image(snapshot_image3,
                expiration_date=self.mock_datetime - datetime.timedelta(0, 1))
        self.create_cached_snapshot_image(snapshot_image4, expiration_date=None)

        cached_snapshot_ids = [s.id for s in gc.get_cached_snapshot_images('cluster')]

        assert len(cached_snapshot_ids) == 2
        assert snapshot_image1.id in cached_snapshot_ids
        assert snapshot_image2.id in cached_snapshot_ids

    @mock.patch('changes.lib.snapshot_garbage_collection.get_current_datetime')
    def test_cache_snapshot_images_have_no_expiration(self, get_current_datetime):
        project = self.create_project()
        snapshot = self.create_snapshot(project)
        plans = [self.create_plan(project) for _ in range(3)]
        snapshot_images = [self.create_snapshot_image(snapshot, plan) for plan in plans]
        snapshot_image_ids = [image.id for image in snapshot_images]

        get_current_datetime.return_value = self.mock_datetime

        gc.cache_snapshot(snapshot)
        assert not db.session.query(CachedSnapshotImage.query.filter(
            CachedSnapshotImage.id.in_(snapshot_image_ids),
            CachedSnapshotImage.expiration_date != None,  # NOQA
        ).exists()).scalar()

    @mock.patch('changes.lib.snapshot_garbage_collection.get_current_datetime')
    def test_cache_snapshot_images_have_no_expiration_with_old(self, get_current_datetime):
        project = self.create_project()
        old_snapshot = self.create_snapshot(project)
        snapshot = self.create_snapshot(project)
        plans = [self.create_plan(project) for _ in range(3)]

        for plan in plans:
            old_snapshot_image = self.create_snapshot_image(old_snapshot, plan)
            self.create_cached_snapshot_image(old_snapshot_image)

        snapshot_images = [self.create_snapshot_image(snapshot, plan) for plan in plans]
        snapshot_image_ids = [image.id for image in snapshot_images]

        get_current_datetime.return_value = self.mock_datetime

        gc.cache_snapshot(snapshot)
        assert not db.session.query(CachedSnapshotImage.query.filter(
            CachedSnapshotImage.id.in_(snapshot_image_ids),
            CachedSnapshotImage.expiration_date != None,  # NOQA
        ).exists()).scalar()

    @mock.patch('changes.lib.snapshot_garbage_collection.get_current_datetime')
    def test_cache_snapshot_expires_old_snapshot(self, get_current_datetime):
        project = self.create_project()
        plans = [self.create_plan(project) for _ in range(3)]

        old_snapshot = self.create_snapshot(project)
        old_snapshot_images = [self.create_snapshot_image(old_snapshot, plan) for plan in plans]
        old_snapshot_image_ids = [image.id for image in old_snapshot_images]

        snapshot = self.create_snapshot(project)
        snapshot_images = [self.create_snapshot_image(snapshot, plan) for plan in plans]

        for old_snapshot_image in old_snapshot_images:
            self.create_cached_snapshot_image(old_snapshot_image)

        get_current_datetime.return_value = self.mock_datetime

        gc.cache_snapshot(snapshot)
        # Ensure that the old snapshots now expire sometime in the future
        assert not db.session.query(CachedSnapshotImage.query.filter(
            CachedSnapshotImage.id.in_(old_snapshot_image_ids),
            sqlalchemy.or_(
                CachedSnapshotImage.expiration_date == None,  # NOQA
                CachedSnapshotImage.expiration_date <= self.mock_datetime
            )
        ).exists()).scalar()

    @mock.patch('changes.lib.snapshot_garbage_collection.get_current_datetime')
    def test_recache_existing_cached_snapshot(self, get_current_datetime):
        """
        In some cases we may want to re-cache an existing snapshot that
        already has an entry in the cache. This should be transparent.
        """
        project = self.create_project()
        plan = self.create_plan(project)
        snapshot = self.create_snapshot(project)
        snapshot_image = self.create_snapshot_image(snapshot, plan)

        get_current_datetime.return_value = self.mock_datetime

        self.create_cached_snapshot_image(snapshot_image,
            expiration_date=self.mock_datetime - datetime.timedelta(0, 1))
        gc.cache_snapshot(snapshot)

        # The old snapshot now has no expiration
        cached_snapshot_image = CachedSnapshotImage.query.get(snapshot_image.id)
        assert cached_snapshot_image is not None
        assert cached_snapshot_image.expiration_date is None

        # and is the only snapshot in existence
        assert CachedSnapshotImage.query.count() == 1

    @mock.patch('changes.lib.snapshot_garbage_collection.get_current_datetime')
    def test_get_relevant_snapshot_images_simple(self, get_current_datetime):
        project = self.create_project()
        plan1 = self.create_plan(project)
        plan2 = self.create_plan(project)
        plan3 = self.create_plan(project)
        plan4 = self.create_plan(project)
        plan5 = self.create_plan(project)

        self.create_step(plan1, data={'cluster': 'cluster1'})
        self.create_step(plan2, data={'cluster': 'cluster1'})
        self.create_step(plan3, data={'cluster': 'cluster2'})
        self.create_step(plan4, data={})
        self.create_step(plan5)

        snapshot = self.create_snapshot(project)
        snapshot_image1 = self.create_snapshot_image(snapshot, plan1)
        snapshot_image2 = self.create_snapshot_image(snapshot, plan2)
        snapshot_image3 = self.create_snapshot_image(snapshot, plan3)
        snapshot_image4 = self.create_snapshot_image(snapshot, plan4)
        snapshot_image5 = self.create_snapshot_image(snapshot, plan5)

        get_current_datetime.return_value = self.mock_datetime
        gc.cache_snapshot(snapshot)

        images = gc.get_relevant_snapshot_images(snapshot.id)
        assert len(images) == 2
        assert 'cluster1' in images
        assert 'cluster2' in images
        assert len(images['cluster1']) == 2
        assert snapshot_image1 in images['cluster1']
        assert snapshot_image2 in images['cluster1']
        assert len(images['cluster2']) == 1
        assert snapshot_image3 in images['cluster2']

    @mock.patch('changes.lib.snapshot_garbage_collection.get_current_datetime')
    def test_get_relevant_snapshot_images_across_projects(self, get_current_datetime):
        project1 = self.create_project()
        project2 = self.create_project()
        plan1_1 = self.create_plan(project1)
        plan1_2 = self.create_plan(project1)
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
        snapshot_image2_1 = self.create_snapshot_image(snapshot2, plan2_1)
        snapshot_image2_2 = self.create_snapshot_image(snapshot2, plan2_2)

        get_current_datetime.return_value = self.mock_datetime
        gc.cache_snapshot(snapshot2)
        gc.cache_snapshot(snapshot1)

        images = gc.get_relevant_snapshot_images(snapshot1.id)
        assert len(images) == 2
        assert 'cluster1' in images
        assert 'cluster2' in images
        assert len(images['cluster1']) == 1
        assert snapshot_image1_1 in images['cluster1']
        assert len(images['cluster2']) == 2
        assert snapshot_image1_2 in images['cluster2']
        assert snapshot_image2_1 in images['cluster2']

    @mock.patch('changes.lib.snapshot_garbage_collection.get_current_datetime')
    def test_clear_expired(self, get_current_datetime):
        project = self.create_project()
        plan1 = self.create_plan(project)
        plan2 = self.create_plan(project)
        plan3 = self.create_plan(project)

        snapshot = self.create_snapshot(project)
        snapshot_image1 = self.create_snapshot_image(snapshot, plan1)
        snapshot_image2 = self.create_snapshot_image(snapshot, plan2)
        snapshot_image3 = self.create_snapshot_image(snapshot, plan3)

        # only the third image has expired. (This is a bit awkward as in a normal
        # situation all images for a snapshot would actually expire simultaneously)
        # since they would have been superceded at the same time, but its easier
        # to only use a single snapshot for testing and the behavior is independent
        # of what snapshot owns them.
        cached_snapshot_image1 = self.create_cached_snapshot_image(snapshot_image1)
        cached_snapshot_image2 = self.create_cached_snapshot_image(snapshot_image2,
            expiration_date=self.mock_datetime + datetime.timedelta(0, 1))
        cached_snapshot_image3 = self.create_cached_snapshot_image(snapshot_image3,
            expiration_date=self.mock_datetime - datetime.timedelta(0, 1))

        get_current_datetime.return_value = self.mock_datetime
        gc.clear_expired()

        assert len(CachedSnapshotImage.query.all()) == 2
        assert CachedSnapshotImage.query.get(cached_snapshot_image1.id) is not None
        assert CachedSnapshotImage.query.get(cached_snapshot_image2.id) is not None
        assert CachedSnapshotImage.query.get(cached_snapshot_image3.id) is None
