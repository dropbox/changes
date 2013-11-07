from changes.api.serializer import Serializer, register
from changes.models.test import TestCase


@register(TestCase)
class TestCaseSerializer(Serializer):
    def serialize(self, instance):
        return {
            'id': instance.id.hex,
            'name': instance.name,
            'package': instance.package,
            'result': instance.result,
            'duration': instance.duration,
            'message': instance.message,
            'dateCreated': instance.date_created,
        }
