from changes.api.serializer import Serializer, register
from changes.models import Event


@register(Event)
class EventSerializer(Serializer):
    def serialize(self, instance, attrs):
        return {
            'id': instance.id.hex,
            'type': instance.type,
            'itemId': instance.item_id.hex,
            'data': dict(instance.data),
            'dateCreated': instance.date_created.isoformat(),
            'dateModified': instance.date_modified.isoformat(),
        }
