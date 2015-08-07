from changes.api.serializer import Crumbler, register
from changes.models.log import LogSource


@register(LogSource)
class LogSourceCrumbler(Crumbler):
    def crumble(self, instance, attrs):
        return {
            'id': instance.id.hex,
            'job': {
                'id': instance.job_id.hex,
            },
            'name': instance.name,
            'step': instance.step,
            'dateCreated': instance.date_created,
        }
