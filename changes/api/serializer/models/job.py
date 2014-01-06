from changes.api.serializer import Serializer, register
from changes.models import Job


@register(Job)
class JobSerializer(Serializer):
    def serialize(self, instance):
        if instance.project_id:
            avg_build_time = instance.project.avg_build_time
        else:
            avg_build_time = None

        data = instance.data or {}
        backend_details = data.get('backend')
        if backend_details:
            external = {
                'link': backend_details['uri'],
                'label': backend_details['label'],
            }
        else:
            external = None

        return {
            'id': instance.id.hex,
            'number': instance.number,
            'name': instance.label,
            'result': instance.result,
            'status': instance.status,
            'project': instance.project,
            'duration': instance.duration,
            'estimatedDuration': avg_build_time,
            'link': '/jobs/%s/' % (instance.id.hex,),
            'external': external,
            'dateCreated': instance.date_created.isoformat(),
            'dateModified': instance.date_modified.isoformat() if instance.date_modified else None,
            'dateStarted': instance.date_started.isoformat() if instance.date_started else None,
            'dateFinished': instance.date_finished.isoformat() if instance.date_finished else None,
        }
