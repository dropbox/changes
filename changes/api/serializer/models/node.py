from changes.api.serializer import Crumbler, register
from changes.models import Node


@register(Node)
class NodeCrumbler(Crumbler):
    def crumble(self, instance, attrs):
        return {
            'id': instance.id.hex,
            'name': instance.label,
            'dateCreated': instance.date_created,
        }
