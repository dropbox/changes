from changes.api.serializer import Crumbler, register
from changes.models import TestArtifact


@register(TestArtifact)
class TestArtifactCrumbler(Crumbler):
    def crumble(self, instance, attrs):
        return {
            'id': instance.id.hex,
            'name': instance.name,
            'url': instance.file.url_for() if instance.file else None,
            'type': instance.type
        }
