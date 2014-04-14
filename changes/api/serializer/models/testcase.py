from changes.api.serializer import Serializer, register
from changes.models.test import TestCase


@register(TestCase)
class TestCaseSerializer(Serializer):
    def serialize(self, instance, attrs):
        return {
            'id': instance.id.hex,
            'hash': instance.name_sha,
            'job': {'id': instance.job_id.hex},
            'project': {'id': instance.project_id.hex},
            'name': instance.name,
            'package': instance.package,
            'shortName': instance.short_name,
            'duration': instance.duration or 0,
            'result': instance.result,
            'numRetries': instance.reruns or 0,
            'dateCreated': instance.date_created,
        }


class TestCaseWithJobSerializer(TestCaseSerializer):
    def serialize(self, instance, attrs):
        data = super(TestCaseWithJobSerializer, self).serialize(instance, attrs)
        data['job'] = instance.job
        return data


class TestCaseWithOriginSerializer(TestCaseSerializer):
    def serialize(self, instance, attrs):
        data = super(TestCaseWithOriginSerializer, self).serialize(instance, attrs)
        data['origin'] = getattr(instance, 'origin', None)
        return data


class GeneralizedTestCase(Serializer):
    def serialize(self, instance, attrs):
        return {
            'hash': instance.name_sha,
            'project': {'id': instance.project_id.hex},
            'duration': instance.duration or 0,
            'name': instance.name,
            'package': instance.package,
            'shortName': instance.short_name,
        }
