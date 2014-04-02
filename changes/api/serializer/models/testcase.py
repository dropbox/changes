from changes.api.serializer import Serializer, register
from changes.models.test import TestCase


@register(TestCase)
class TestCaseSerializer(Serializer):
    def serialize(self, instance, attrs):
        if not instance.package:
            try:
                package, name = instance.name.rsplit(instance.sep, 1)
            except ValueError:
                package, name = None, instance.name
        else:
            package, name = instance.package, instance.name

        return {
            'id': instance.id.hex,
            'name': name,
            'package': package,
            'result': instance.result,
            'duration': instance.duration,
            'message': instance.message,
            'dateCreated': instance.date_created,
        }
