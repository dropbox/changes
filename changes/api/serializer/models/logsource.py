from changes.api.serializer import Serializer, register
from changes.models.log import LogSource


@register(LogSource)
class LogSourceSerializer(Serializer):
    def serialize(self, instance):
        return {
            'id': instance.id.hex,
            'name': instance.name,
            'link': '/builds/{0}/logs/{1}/'.format(
                instance.job_id.hex, instance.id.hex),
            'dateCreated': instance.date_created,
        }
