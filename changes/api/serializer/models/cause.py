from changes.api.serializer import Serializer, register
from changes.constants import Cause


@register(Cause)
class CauseSerializer(Serializer):
    def serialize(self, instance):
        return {
            'id': instance.name,
            'name': unicode(instance),
        }
