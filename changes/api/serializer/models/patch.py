from changes.api.serializer import Serializer, register
from changes.models.patch import Patch


@register(Patch)
class PatchSerializer(Serializer):
    def serialize(self, instance):
        return {
            'id': instance.id.hex,
            'name': instance.label,
            'message': instance.message,
            'diff': instance.diff,
            'link': '/patches/{0}/'.format(instance.id.hex),
            'parentRevision': {
                'sha': instance.parent_revision_sha,
            },
            'dateCreated': instance.date_created,
        }
