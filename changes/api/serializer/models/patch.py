from changes.api.serializer import Serializer, register
from changes.models.patch import Patch
from changes.utils.http import build_uri


@register(Patch)
class PatchSerializer(Serializer):
    def serialize(self, instance, attrs):
        return {
            'id': instance.id.hex,
            'diff': instance.diff,
            'link': build_uri('/patches/{0}/'.format(instance.id.hex)),
            'parentRevision': {
                'sha': instance.parent_revision_sha,
            },
            'dateCreated': instance.date_created,
        }
