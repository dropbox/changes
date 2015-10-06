from changes.api.serializer import Crumbler, register
from changes.models import JobStep


@register(JobStep)
class JobStepCrumbler(Crumbler):
    def crumble(self, instance, attrs):
        return {
            'id': instance.id.hex,
            'name': instance.label,
            'phase': {
                'id': instance.phase_id.hex,
            },
            'data': dict(instance.data),
            'result': instance.result,
            'status': instance.status,
            'node': instance.node,
            'duration': instance.duration,
            'replacement_id': instance.replacement_id,
            'dateCreated': instance.date_created,
            'dateStarted': instance.date_started,
            'dateFinished': instance.date_finished,
        }
