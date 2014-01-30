from changes.api.serializer import Serializer, register
from changes.models import Comment


@register(Comment)
class CommentSerializer(Serializer):
    def serialize(self, instance):
        return {
            'id': instance.id.hex,
            'user': instance.user,
            'text': instance.text,
            'dateCreated': instance.date_created.isoformat(),
        }
