from changes.api.serializer import Serializer, register
from changes.constants import Result
from changes.models.test import TestGroup


@register(TestGroup)
class TestGroupSerializer(Serializer):
    def serialize(self, instance):
        if instance.parent:
            short_name = instance.name[len(instance.parent.name) + 1:]
        else:
            short_name = instance.name

        return {
            'id': instance.id.hex,
            'name': instance.name,
            'shortName': short_name,
            'duration': instance.duration or 0,
            'result': instance.result or Result.unknown,
            'numTests': instance.num_tests or 0,
            'numFailures': instance.num_failed or 0,
            'link': '/testgroups/%s/' % (instance.id.hex,),
            'dateCreated': instance.date_created,
        }


class TestGroupWithBuildSerializer(TestGroupSerializer):
    def serialize(self, instance):
        data = super(TestGroupWithBuildSerializer, self).serialize(instance)
        data['build'] = instance.job
        return data


class TestGroupWithOriginSerializer(TestGroupSerializer):
    def serialize(self, instance):
        data = super(TestGroupWithOriginSerializer, self).serialize(instance)
        data['origin'] = getattr(instance, 'origin', None)
        return data
