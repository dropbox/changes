from changes.api.serializer import Crumbler, register
from changes.models.adminmessage import AdminMessage


@register(AdminMessage)
class AdminMessageCrumbler(Crumbler):
    def crumble(self, instance, attrs):
        return {
            'id': instance.id.hex,
            'user': instance.user,
            'message': instance.message,
            'dateCreated': instance.date_created,
        }
