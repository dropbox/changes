from changes.api.serializer import Serializer, register
from changes.models.change import Change


@register(Change)
class ChangeSerializer(Serializer):
    def serialize(self, instance):
        result = {
            'id': instance.id.hex,
            'name': instance.label,
            'project': instance.project,
            'author': instance.author,
            'link': '/projects/%s/changes/%s/' % (instance.project.slug, instance.id.hex),
            'dateCreated': instance.date_created.isoformat(),
        }
        if hasattr(instance, 'last_build'):
            result['lastBuild'] = instance.last_build
        return result
