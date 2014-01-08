from changes.api.serializer import Serializer, register
from changes.models.change import Change
from changes.utils.http import build_uri


@register(Change)
class ChangeSerializer(Serializer):
    def serialize(self, instance):
        result = {
            'id': instance.id.hex,
            'name': instance.label,
            'project': instance.project,
            'author': instance.author,
            'message': instance.message,
            'link': build_uri('/changes/%s/' % (instance.id.hex,)),
            'dateCreated': instance.date_created.isoformat(),
            'dateModified': instance.date_modified.isoformat(),
        }
        if hasattr(instance, 'last_job'):
            result['lastBuild'] = instance.last_job
        return result
