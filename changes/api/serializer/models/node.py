from changes.api.serializer import Crumbler, register
from changes.models.node import Node


@register(Node)
class NodeCrumbler(Crumbler):
    def crumble(self, instance, attrs):
        return {
            'id': instance.id.hex,
            'name': instance.label,
            'dateCreated': instance.date_created,
        }
