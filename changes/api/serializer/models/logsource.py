from changes.api.serializer import Serializer, register
from changes.models.log import LogSource
from changes.utils.http import build_uri


@register(LogSource)
class LogSourceSerializer(Serializer):
    def serialize(self, instance):
        return {
            'id': instance.id.hex,
            'name': instance.name,
            'link': build_uri('/jobs/{0}/logs/{1}/'.format(
                instance.job_id.hex, instance.id.hex)),
            'dateCreated': instance.date_created,
        }
