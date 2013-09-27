from changes.api.serializer import Serializer, register
from changes.constants import Result


@register(Result)
class ResultSerializer(Serializer):
    def serialize(self, instance):
        return {
            'id': instance.name,
            'name': unicode(instance),
        }
