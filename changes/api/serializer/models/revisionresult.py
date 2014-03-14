from changes.api.serializer import Serializer, register
from changes.vcs.base import RevisionResult


@register(RevisionResult)
class RevisionSerializer(Serializer):
    def serialize(self, instance, attrs):
        return {
            'id': instance.id,
            'message': instance.message,
            'author': None,  # We don't return author information
            'dateCreated': instance.author_date,
        }
