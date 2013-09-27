from changes.api.serializer import Serializer, register
from changes.constants import Status


@register(Status)
class StatusSerializer(Serializer):
    def serialize(self, instance):
        return {
            'id': instance.name,
            'name': unicode(instance),
        }
