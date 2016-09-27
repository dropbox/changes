from __future__ import absolute_import

from changes.api.serializer import Crumbler, register
from changes.models.revisionresult import RevisionResult


@register(RevisionResult)
class RevisionResultCrumbler(Crumbler):
    def crumble(self, instance, attrs):
        return {
            'id': instance.id.hex,
            'revisionSha': instance.revision_sha,
            'build': instance.build,
            'result': instance.result,
        }
