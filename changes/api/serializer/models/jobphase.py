from changes.api.serializer import Crumbler, register
from changes.models import JobPhase


@register(JobPhase)
class JobPhaseCrumbler(Crumbler):
    def crumble(self, instance, attrs):
        return {
            'id': instance.id.hex,
            'name': instance.label,
            'result': instance.result,
            'status': instance.status,
            'duration': instance.duration,
            'dateCreated': instance.date_created,
            'dateStarted': instance.date_started,
            'dateFinished': instance.date_finished,
        }


class JobPhaseWithStepsCrumbler(JobPhaseCrumbler):
    def crumble(self, instance, attrs):
        data = super(JobPhaseWithStepsCrumbler, self).crumble(instance, attrs)
        data['steps'] = list(instance.steps)
        return data
