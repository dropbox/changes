from changes.api.serializer import Crumbler, register
from changes.models.bazeltarget import BazelTarget


@register(BazelTarget)
class BazelTargetCrumbler(Crumbler):
    def crumble(self, instance, attrs):
        return {
            'id': instance.id.hex,
            'job': {'id': instance.job_id.hex},
            'step': {'id': instance.step_id.hex},
            'name': instance.name,
            'duration': instance.duration or 0,
            'status': instance.status,
            'result': instance.result,
            'dateCreated': instance.date_created,
        }
