from changes.api.serializer import Serializer, register
from changes.models import Source


@register(Source)
class SourceSerializer(Serializer):
    def serialize(self, instance):
        if instance.patch_id:
            patch = {
                'id': instance.patch_id.hex,
            }
        else:
            patch = None

        return {
            'id': instance.id.hex,
            'patch': patch,
            'revision': {
                'sha': instance.revision_sha
            },
            'dateCreated': instance.date_created,
        }
