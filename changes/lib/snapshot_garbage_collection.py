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
import sqlalchemy
from changes.config import db
from changes.models import CachedSnapshotImage, Plan, SnapshotImage
from datetime import datetime


def get_current_datetime():
    """Gets the current datettime. Equivalent to datettime.utcnow().

    We can't mock datetime - so we abstract to this.
    """
    return datetime.utcnow()


def get_plans_for_cluster(cluster):
    """
    Aggregate all plans that the given cluster is associated with

    Cluster is not a column of plan so we can't do a more
    efficient join operation here. A consequence of refusing to
    store jenkins-specific things in the database is that we can't
    do natural operations on the database.
    """
    plans = []
    for plan in db.session.query(Plan).all():
        if plan.data and plan.data.get('cluster', None) == cluster:
            plans.extend([plan])
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
    if plan_ids == []:
        return []

    return db.session.query(SnapshotImage).filter(
        sqlalchemy.or_(
            CachedSnapshotImage.expiration_date == None,  # NOQA
            now <= CachedSnapshotImage.expiration_date,
        ),
        CachedSnapshotImage.id == SnapshotImage.id,
        SnapshotImage.plan_id.in_(plan_ids)
    ).all()
