from changes.api.serializer import Serializer, register
from changes.models.revision import Revision


@register(Revision)
class RevisionSerializer(Serializer):
    def serialize(self, instance):
        return {
            'id': instance.sha,
            'message': instance.message,
            'author': instance.author,
            'dateCreated': instance.date_created,
        }
