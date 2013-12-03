from changes.api.serializer import Serializer, register
from changes.models.repository import Repository


@register(Repository)
class RepositorySerializer(Serializer):
    def serialize(self, instance):
        return {
            'id': instance.id.hex,
            'url': instance.url,
        }
