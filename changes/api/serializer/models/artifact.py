from changes.api.serializer import Crumbler, register
from changes.models import Artifact


@register(Artifact)
class ArtifactCrumbler(Crumbler):
    def crumble(self, instance, attrs):
        return {
            'id': instance.id.hex,
            'jobstep': instance.step,
            'name': instance.name,
            'url': instance.file.url_for() if instance.file else None,
            'dateCreated': instance.date_created,
        }
