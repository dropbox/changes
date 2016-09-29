from changes.api.serializer import Crumbler, register
from changes.constants import ResultSource
from changes.models.bazeltarget import BazelTarget


@register(BazelTarget)
class BazelTargetCrumbler(Crumbler):
    def crumble(self, instance, attrs):
        result = {
            'id': instance.id.hex,
            'job': {'id': instance.job_id.hex},
            'name': instance.name,
            'duration': instance.duration or 0,
            'status': instance.status,
            'result': instance.result,
            'resultSource': instance.result_source or ResultSource.from_self,
            'dateCreated': instance.date_created,
        }
        if instance.step_id:
            result['step'] = {'id': instance.step_id.hex}
        return result
