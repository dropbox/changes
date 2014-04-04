from changes.api.serializer import Serializer, register
from changes.constants import Result
from changes.models.test import TestGroup


@register(TestGroup)
class TestGroupSerializer(Serializer):
    def serialize(self, instance, attrs):
        data = {
            'id': instance.id.hex,
            'job': {'id': instance.job_id.hex},
            'project': {'id': instance.project_id.hex},
            'name': instance.name,
            'shortName': instance.short_name,
            'duration': instance.duration or 0,
            'result': instance.result or Result.unknown,
            'numTests': instance.num_tests or 0,
            'numFailures': instance.num_failed or 0,
            'dateCreated': instance.date_created,
        }
        return data


class TestGroupWithJobSerializer(TestGroupSerializer):
    def serialize(self, instance, attrs):
        data = super(TestGroupWithJobSerializer, self).serialize(instance, attrs)
        data['job'] = instance.job
        return data


class TestGroupWithOriginSerializer(TestGroupWithJobSerializer):
    def serialize(self, instance, attrs):
        data = super(TestGroupWithOriginSerializer, self).serialize(instance, attrs)
        data['origin'] = getattr(instance, 'origin', None)
        return data
