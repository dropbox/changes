from changes.api.serializer import Serializer, register
from changes.models.repository import Repository, RepositoryBackend


@register(Repository)
class RepositorySerializer(Serializer):
    def serialize(self, instance, attrs):
        return {
            'id': instance.id.hex,
            'url': instance.url,
            'backend': instance.backend,
            'status': instance.status,
            'dateCretaed': instance.date_created,
        }


@register(RepositoryBackend)
class RepositoryBackendSerializer(Serializer):
    def serialize(self, instance, attrs):
        return {
            'id': instance.name,
            'name': unicode(instance),
        }
