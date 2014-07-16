from changes.api.serializer import Serializer, register
from changes.models import Command


@register(Command)
class CommandSerializer(Serializer):
    def serialize(self, instance, attrs):
        return {
            'id': instance.id.hex,
            'name': instance.label,
            'status': instance.status,
            'script': instance.script,
            'returnCode': instance.return_code,
            'env': instance.env,
            'cwd': instance.cwd,
            'artifacts': instance.artifacts or [],
            'duration': instance.duration,
            'dateCreated': instance.date_created,
            'dateStarted': instance.date_started,
            'dateFinished': instance.date_finished,
        }
