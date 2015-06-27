from __future__ import absolute_import

from changes.api.base import APIView
import changes.lib.snapshot_garbage_collection as gc


class CachedSnapshotClusterDetailsAPIView(APIView):
    def get(self, cluster):
        images = gc.get_cached_snapshot_images(cluster)
        return self.respond([image.id for image in images])
