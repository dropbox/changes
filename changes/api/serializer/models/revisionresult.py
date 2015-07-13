from changes.api.serializer import Serializer, register
from changes.vcs.base import RevisionResult


@register(RevisionResult)
class RevisionSerializer(Serializer):
    def serialize(self, instance, attrs):
        return {
            'id': instance.id,
            'sha': instance.id,  # Having both id and sha is a bit distasteful. We should try to fix this.
            'message': instance.message,
            'author': None,  # We don't return author information
            'dateCreated': instance.author_date,
            'dateCommitted': instance.committer_date,
            'branches': instance.branches,
        }
