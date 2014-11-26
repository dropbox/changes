from changes.api.serializer import Serializer, register
from changes.models import TestArtifact


@register(TestArtifact)
class TestArtifactSerializer(Serializer):
    def serialize(self, instance, attrs):
        return {
            'id': instance.id.hex,
            'name': instance.name,
            'url': instance.file.url_for() if instance.file else None,
            'type': instance.type
        }
