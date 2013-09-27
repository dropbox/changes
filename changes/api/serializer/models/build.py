from changes.api.serializer import Serializer, register
from changes.models.build import Build


@register(Build)
class BuildSerializer(Serializer):
    def serialize(self, instance):
        return {
            'id': instance.id.hex,
            'name': instance.label,
            'result': instance.result,
            'status': instance.status,
            'project': instance.project,
            'author': instance.author,
            'parent_revision': {
                'sha': instance.parent_revision_sha,
            },
            'duration': instance.duration,
            'link': '/projects/%s/builds/%s/' % (instance.project.slug, instance.id.hex),
            'dateCreated': instance.date_created.isoformat(),
            'dateStarted': instance.date_started.isoformat() if instance.date_started else None,
            'dateFinished': instance.date_finished.isoformat() if instance.date_finished else None,
            'progress': instance.progress,
        }
