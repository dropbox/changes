from changes.api.serializer import Serializer, register
from changes.models import Cluster


@register(Cluster)
class ClusterSerializer(Serializer):
    def serialize(self, instance, attrs):
        return {
            'id': instance.id.hex,
            'name': instance.label,
            'dateCreated': instance.date_created,
        }
