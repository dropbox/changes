
from changes.api.serializer import Crumbler, register
from changes.models.log import LogChunk


@register(LogChunk)
class LogChunkCrumbler(Crumbler):
    def crumble(self, instance, attrs):
        return {
            'id': instance.id.hex,
            'source': {
                'id': instance.source.id.hex,
            },
            'text': instance.text,
            'offset': instance.offset,
            'size': instance.size,
        }
