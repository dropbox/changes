from changes.api.serializer import Crumbler, register
from changes.models import Command


@register(Command)
class CommandCrumbler(Crumbler):
    def crumble(self, instance, attrs):
        return {
            'id': instance.id.hex,
            'name': instance.label,
            'status': instance.status,
            'script': instance.script,
            'returnCode': instance.return_code,
            'env': dict(instance.env or {}),
            'cwd': instance.cwd,
            'type': instance.type,
            'captureOutput': instance.type.is_collector(),
            'artifacts': instance.artifacts or [],
            'duration': instance.duration,
            'dateCreated': instance.date_created,
            'dateStarted': instance.date_started,
            'dateFinished': instance.date_finished,
        }
