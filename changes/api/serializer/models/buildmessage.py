from changes.api.serializer import Crumbler, register
from changes.models.buildmessage import BuildMessage


@register(BuildMessage)
class BuildMessageCrumbler(Crumbler):
    def crumble(self, instance, attrs):
        return {
            'id': instance.id.hex,
            'build': {'id': instance.build_id.hex},
            'text': instance.text,
            'dateCreated': instance.date_created,
        }
