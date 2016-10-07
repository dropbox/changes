from changes.api.serializer import Crumbler, register
from changes.models.bazeltargetmessage import BazelTargetMessage


@register(BazelTargetMessage)
class BazelTargetMessageCrumbler(Crumbler):
    def crumble(self, instance, attrs):
        return {
            'id': instance.id.hex,
            'target': {'id': instance.target_id.hex},
            'text': instance.text,
            'dateCreated': instance.date_created,
        }
