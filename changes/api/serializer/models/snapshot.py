from changes.api.serializer import Serializer, register
from changes.models import Snapshot


@register(Snapshot)
class SnapshotSerializer(Serializer):
    def serialize(self, instance, attrs):
        return {
            'id': instance.id.hex,
            'project_id': instance.project_id.hex,
            'build_id': instance.build_id.hex if instance.build_id else None,
            'status': instance.status,
            'url': instance.url,
        }
