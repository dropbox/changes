from changes.api.serializer import Serializer, register
from changes.models import SnapshotImage


@register(SnapshotImage)
class SnapshotImageSerializer(Serializer):
    def serialize(self, instance, attrs):
        return {
            'id': instance.id.hex,
            'dateCreated': instance.date_created,
        }
