from changes.api.serializer import Serializer, register
from changes.models.revision import Revision


@register(Revision)
class RevisionSerializer(Serializer):
    def serialize(self, instance, attrs):
        return {
            'id': instance.sha,
            'message': instance.message,
            'author': instance.author,
            'parents': instance.parents,
            'branches': instance.branches,
            'dateCreated': instance.date_created,
        }
