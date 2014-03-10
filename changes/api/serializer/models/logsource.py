from changes.api.serializer import Serializer, register
from changes.models.log import LogSource


@register(LogSource)
class LogSourceSerializer(Serializer):
    def serialize(self, instance):
        return {
            'id': instance.id.hex,
            'job': {
                'id': instance.job_id.hex,
            },
            'name': instance.name,
            'step': instance.step,
            'dateCreated': instance.date_created,
        }
