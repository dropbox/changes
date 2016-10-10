from changes.api.serializer import Crumbler, register
from changes.constants import ResultSource
from changes.models.bazeltarget import BazelTarget
from changes.models.bazeltargetmessage import BazelTargetMessage


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


class BazelTargetWithMessagesCrumbler(BazelTargetCrumbler):
    def __init__(self, max_messages, *args, **kwargs):
        super(BazelTargetWithMessagesCrumbler, self).__init__(*args, **kwargs)
        self.max_messages = max_messages

    def crumble(self, instance, attrs):
        data = super(BazelTargetWithMessagesCrumbler, self).crumble(instance, attrs)
        data['messages'] = list(BazelTargetMessage.query.filter(
            BazelTargetMessage.target_id == instance.id,
        ).order_by(BazelTargetMessage.date_created).limit(self.max_messages))
        return data
