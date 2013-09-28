from changes.api.serializer import Serializer, register
from changes.models.test import Test


@register(Test)
class TestSerializer(Serializer):
    def serialize(self, instance):
        return {
            'id': instance.id.hex,
            'name': instance.label,
            'result': instance.result,
            'duration': instance.duration,
            'message': instance.message,
            'dateCreated': instance.date_created,
        }
