from changes.api.serializer import Crumbler, register
from changes.models import SnapshotImage


@register(SnapshotImage)
class SnapshotImageCrumbler(Crumbler):
    def crumble(self, instance, attrs):
        return {
            'id': instance.id.hex,
            'status': instance.status,
            'dateCreated': instance.date_created,
            'plan': instance.plan,
            'snapshot': {'id': instance.snapshot.id.hex},
        }
