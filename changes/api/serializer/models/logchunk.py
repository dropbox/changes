from ansi2html import Ansi2HTMLConverter

from flask import current_app
from werkzeug.utils import escape

from changes.api.serializer import Serializer, register
from changes.models.log import LogChunk


@register(LogChunk)
class LogChunkSerializer(Serializer):
    def serialize(self, instance, attrs):
        conv = Ansi2HTMLConverter()
        try:
            formatted_text = conv.convert(instance.text, full=False)
        except Exception:
            current_app.logger.exception('Unable to convert ansi to html: %s', instance.text)
            formatted_text = escape(instance.text)

        return {
            'id': instance.id.hex,
            'source': {
                'id': instance.source.id.hex,
            },
            'text': formatted_text,
            'offset': instance.offset,
            'size': instance.size,
        }
