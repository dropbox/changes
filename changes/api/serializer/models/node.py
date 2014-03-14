from changes.api.serializer import Serializer, register
from changes.models import Node


@register(Node)
class NodeSerializer(Serializer):
    def serialize(self, instance, attrs):
        return {
            'id': instance.id.hex,
            'name': instance.label,
            'dateCreated': instance.date_created,
        }
