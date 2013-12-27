from ansi2html import Ansi2HTMLConverter

from changes.api.serializer import Serializer, register
from changes.models.log import LogChunk


@register(LogChunk)
class LogChunkSerializer(Serializer):
    def serialize(self, instance):
        conv = Ansi2HTMLConverter()
        formatted_text = conv.convert(instance.text, full=False)

        return {
            'id': instance.id.hex,
            'source': {
                'id': instance.source_id.hex,
            },
            'text': formatted_text,
            'offset': instance.offset,
            'size': instance.size,
        }
