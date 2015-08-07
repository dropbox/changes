from changes.api.serializer import Crumbler, register
from changes.models.test import TestCase


@register(TestCase)
class TestCaseCrumbler(Crumbler):
    def crumble(self, instance, attrs):
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


class TestCaseWithJobCrumbler(TestCaseCrumbler):
    def crumble(self, instance, attrs):
        data = super(TestCaseWithJobCrumbler, self).crumble(instance, attrs)
        data['job'] = instance.job
        return data


class TestCaseWithOriginCrumbler(TestCaseCrumbler):
    def crumble(self, instance, attrs):
        data = super(TestCaseWithOriginCrumbler, self).crumble(instance, attrs)
        data['origin'] = getattr(instance, 'origin', None)
        return data


class GeneralizedTestCase(Crumbler):
    def crumble(self, instance, attrs):
        return {
            'hash': instance.name_sha,
            'project': {'id': instance.project_id.hex},
            'duration': instance.duration or 0,
            'name': instance.name,
            'package': instance.package,
            'shortName': instance.short_name,
        }
