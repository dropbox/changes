from changes.api.serializer import Serializer, register
from changes.models.log import LogChunk


@register(LogChunk)
class LogChunkSerializer(Serializer):
    def serialize(self, instance):
        return {
            'source': {
                'id': instance.source_id.hex,
            },
            'text': instance.text,
            'offset': instance.offset,
            'size': instance.size,
        }
