from changes.api.serializer import Serializer, register
from changes.models.test import TestGroup


@register(TestGroup)
class TestGroupSerializer(Serializer):
    def serialize(self, instance):
        return {
            'id': instance.id.hex,
            'name': instance.name,
            'duration': instance.duration or 0,
            'numTests': instance.num_tests or 0,
            'numFailures': instance.num_failed or 0,
            # 'link': '/tests/%s/' % (instance.id.hex,),
            'dateCreated': instance.date_created,
        }
