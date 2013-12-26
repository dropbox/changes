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

        if instance.parent_id:
            parent = {
                'id': instance.parent_id.hex,
                'link': '/builds/%s/' % (instance.parent_id.hex,),
            }
        else:
            parent = None

        target = instance.target
        if target is None and instance.revision_sha:
                target = instance.revision_sha[:12]

        if instance.revision_sha:
            revision = {
                'sha': instance.revision_sha,
            }
        else:
            revision = None

        if instance.patch_id:
            patch = {
                'id': instance.patch_id.hex,
            }
        else:
            patch = None

        return {
            'id': instance.id.hex,
            'name': instance.label,
            'target': target,
            'result': instance.result,
            'status': instance.status,
            'project': instance.project,
            'cause': instance.cause,
            'author': instance.author,
            'revision': revision,
            'patch': patch,
            'parent': parent,
            'message': instance.message,
            'duration': instance.duration,
            'estimatedDuration': avg_build_time,
            'link': '/builds/%s/' % (instance.id.hex,),
            'external': external,
            'dateCreated': instance.date_created.isoformat(),
            'dateModified': instance.date_modified.isoformat() if instance.date_modified else None,
            'dateStarted': instance.date_started.isoformat() if instance.date_started else None,
            'dateFinished': instance.date_finished.isoformat() if instance.date_finished else None,
        }
