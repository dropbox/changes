from __future__ import absolute_import

from changes.api.serializer import Serializer, register
from changes.models import Source


@register(Source)
class SourceSerializer(Serializer):
    def serialize(self, instance, attrs):
        if instance.patch_id:
            if instance.data.get('phabricator.revisionURL'):
                external = {
                    'link': instance.data['phabricator.revisionURL'],
                    'label': 'D{}'.format(instance.data['phabricator.revisionID']),
                }
            else:
                external = None

            patch = {
                'id': instance.patch_id.hex,
                'external': external,
            }
        else:
            patch = None

        return {
            'id': instance.id.hex,
            'patch': patch,
            'revision': instance.revision,
            'isCommit': instance.is_commit(),
            'dateCreated': instance.date_created,
            'data': dict(instance.data or {}),
        }
