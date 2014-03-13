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

        data = {
            'id': instance.id.hex,
            'job': {'id': instance.job_id.hex},
            'project': {'id': instance.project_id.hex},
            'name': instance.name,
            'shortName': short_name,
            'duration': instance.duration or 0,
            'result': instance.result or Result.unknown,
            'numTests': instance.num_tests or 0,
            'numFailures': instance.num_failed or 0,
            'dateCreated': instance.date_created,
        }
        return data


class TestGroupWithJobSerializer(TestGroupSerializer):
    def serialize(self, instance):
        data = super(TestGroupWithJobSerializer, self).serialize(instance)
        data['job'] = instance.job
        return data


class TestGroupWithOriginSerializer(TestGroupWithJobSerializer):
    def serialize(self, instance):
        data = super(TestGroupWithOriginSerializer, self).serialize(instance)
        data['origin'] = getattr(instance, 'origin', None)
        return data
