from changes.api.serializer import Serializer, register
from changes.models import AdminMessage


@register(AdminMessage)
class AdminMessageSerializer(Serializer):
    def serialize(self, instance, attrs):
        return {
            'id': instance.id.hex,
            'user': instance.user,
            'message': instance.message,
            'dateCreated': instance.date_created,
        }
