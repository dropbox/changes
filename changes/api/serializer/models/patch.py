from __future__ import absolute_import

from changes.api.serializer import Crumbler, register
from changes.models.patch import Patch
from changes.utils.http import build_uri


@register(Patch)
class PatchCrumbler(Crumbler):
    def crumble(self, instance, attrs):
        return {
            'id': instance.id.hex,
            'diff': instance.diff,
            'link': build_uri('/patches/{0}/'.format(instance.id.hex)),
            'parentRevision': {
                'sha': instance.parent_revision_sha,
            },
            'dateCreated': instance.date_created,
        }
