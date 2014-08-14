from changes.api.serializer import Serializer, register
from changes.models import Artifact


@register(Artifact)
class ArtifactSerializer(Serializer):
    def serialize(self, instance, attrs):
        return {
            'id': instance.id.hex,
            'jobstep': instance.step,
            'name': instance.name,
            'url': instance.file.url_for() if instance.file else None,
            'dateCreated': instance.date_created,
        }
