from __future__ import absolute_import

from changes.api.base import APIView
from changes.models import Snapshot
import changes.lib.snapshot_garbage_collection as gc


class CachedSnapshotDetailsAPIView(APIView):
    def unpack_snapshot_ids(self, cluster_map):
        return {cluster: [i.id.hex for i in images] for cluster, images in cluster_map.iteritems()}

    def post(self, snapshot_id):
        """
        Add the snapshot images of a given snapshot to the cache and respond
        with sync updates for all of the clusters associated with the snapshot
        that was just updated.
        """
        snapshot = Snapshot.query.get(snapshot_id)
        if snapshot is None:
            return '', 404

        # Add the snapshot to the cache, giving it no expiration
        gc.cache_snapshot(snapshot)

        # Send back the sync information for all clusters which require
        # an update. Because this response is intended to be used for
        # syncing we don't need to send anything but the snapshot
        # image ids.
        response = gc.get_relevant_snapshot_images(snapshot.id)
        return self.respond(self.unpack_snapshot_ids(response))
