from changes.api.serializer import Crumbler, register
from changes.models import Comment


@register(Comment)
class CommentCrumbler(Crumbler):
    def crumble(self, instance, attrs):
        return {
            'id': instance.id.hex,
            'user': instance.user,
            'text': instance.text,
            'dateCreated': instance.date_created.isoformat(),
        }
