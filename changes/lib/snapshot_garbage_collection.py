"""Utilities related to cached snapshots and garbage collection logic.

The snapshot garbage collection service works by maintaining a master
list of which snapshots a given cluster should use. There are only two
operations that can be made to the the garbage collection api: sync
and update.

Syncing to the garbage collection is done by sending slaves on a given
cluster the list of snapshot ids they are responsible for having. The
slave is then required to download those snapshots and is free to
remove any not in that list. This corresponds to get_cached_snapshot_images.

Each cached snapshot image at some point will expire after it has been
superceded by a new image (ie, some snapshot was created for the same
project since the original snapshot). When this occurs, the snapshot
image is assigned an expiration date based on the configuration value
SNAPSHOT_EXPIRATION_DELAY (in hours). Lists of snapshot images sent
to slaves will never contain expired snapshot images.

Updating the garbage collection is append-only. When a new snapshot
is added to the cached snapshot system, it automatically sets the
expiration date for the old snapshot images under the same project
and gives the new snapshot no expiration date (it will only receive
one once it has been superceded).

The SNAPSHOT_EXPIRATION_DELAY is used because a constant time has no
real effect as long as it isn't too large and because there may be
builds running still that are using the old images, which would make
deletion potentially unsafe without complex locking on the client side.

This api abstracts away cached snapshot images so that no other parts of
changes have to know about their existance as a table separate from
snapshot imagese.
"""
from changes.config import db
from changes.models import CachedSnapshotImage, Plan, PlanStatus, Snapshot, SnapshotImage, Step
from datetime import datetime
from flask import current_app

import sqlalchemy


def get_current_datetime():
    """Gets the current datettime. Equivalent to datettime.utcnow().

    We can't mock datetime - so we abstract to this.
    """
    return datetime.utcnow()


def get_plans_for_cluster(cluster):
    """Returns the set of active plans for the given cluster.
    """
    plans = set()
    q = db.session.query(Plan, Step)
    q = q.filter(Plan.id == Step.plan_id, Plan.status == PlanStatus.active)
    for plan, step in q.all():
        if step.data and step.data.get('cluster', None) == cluster:
            plans.add(plan)
    return plans


def get_cached_snapshot_images(cluster):
    """Get the cached snapshot images for a specific cluster.

    Return all of the non-expired snapshot images for a specific
    cluster by checking all build plans to see which plans the cluster
    is associated with and grabbing snapshot images for any unexpired
    image associated with those plans.
    """
    now = get_current_datetime()
    plan_ids = [plan.id for plan in get_plans_for_cluster(cluster)]

    # Although performance isn't critical here, this shuts up a warning
    # from sqlalchemy
    if not plan_ids:
        return []

    return db.session.query(SnapshotImage).filter(
        sqlalchemy.or_(
            CachedSnapshotImage.expiration_date == None,  # NOQA
            now <= CachedSnapshotImage.expiration_date,
        ),
        CachedSnapshotImage.id == SnapshotImage.id,
        SnapshotImage.plan_id.in_(plan_ids)
    ).all()


def _cache_image(snapshot_image):
    """Creates a cached image for a given snapshot image.

    We transparently update any existing images with the same id
    in case we are caching a snaphsot that used to be cached but is
    no longer cached. This is useful for example if a snapshot is
    determined to not work and so you need to rewind to a previous
    snapshot that has already expired.
    """
    # The explicit expiration date is necessary because an existing
    # item might already exist with an expiration date, and in that
    # case the expiration date will not change.
    return db.session.merge(
        CachedSnapshotImage(id=snapshot_image.id, expiration_date=None)
    )


def cache_snapshot(snapshot):
    """Update the cache with a newly generated snapshot.

    Caches a new snapshot (by caching all of its images).
    This creates expirations for all cached
    snapshots with no expiration and adds a new cached snapshot
    with no expiration.
    """
    now = get_current_datetime()

    # Query: All cached snapshot images sharing the same project
    CachedSnapshotImage.query.filter(
        CachedSnapshotImage.expiration_date == None,  # NOQA
        CachedSnapshotImage.id == SnapshotImage.id,
        SnapshotImage.snapshot_id == Snapshot.id,
        Snapshot.project_id == snapshot.project_id
    ).update(dict(expiration_date=now + current_app.config['CACHED_SNAPSHOT_EXPIRATION_DELTA']))

    images = SnapshotImage.query.filter(SnapshotImage.snapshot_id == snapshot.id)

    # mark all of the individual snapshot images as cached
    # while transparently updating any snapshot images that
    # were already cached to have no expiration date
    cached_snapshot_images = [_cache_image(image) for image in images]
    db.session.add_all(cached_snapshot_images)

    db.session.commit()


def get_relevant_snapshot_images(snapshot_id):
    """Given a snapshot id, detect the relevant clusters and find their
    cached snapshot images.

    Returns a dict whose keys are clusters that need to be synced
    based on the new snapshot and values are the list of snapshot
    images associated with the snapshot.
    """
    steps = Step.query.filter(
        Plan.id == SnapshotImage.plan_id,
        Step.plan_id == Plan.id,
        SnapshotImage.snapshot_id == snapshot_id
    ).all()

    clusters = set()
    for step in steps:
        if step.data and 'cluster' in step.data:
            clusters.add(step.data['cluster'])

    return dict([(cluster, get_cached_snapshot_images(cluster)) for cluster in clusters])


def clear_expired():
    """Utility function that deletes all expired rows.
    """
    now = get_current_datetime()

    CachedSnapshotImage.query.filter(
        CachedSnapshotImage.expiration_date < now
    ).delete()

    db.session.commit()
