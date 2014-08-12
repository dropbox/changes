from changes.api.serializer import Serializer, register
from changes.models import Snapshot


@register(Snapshot)
class SnapshotSerializer(Serializer):
    def serialize(self, instance, attrs):
        if instance.build_id:
            build = {
                'id': instance.build_id.hex,
            }
        else:
            build = None

        return {
            'id': instance.id.hex,
            'project': {
                'id': instance.project_id.hex,
            },
            'source': instance.source,
            'build': build,
            'status': instance.status,
            'dateCreated': instance.date_created,
        }
