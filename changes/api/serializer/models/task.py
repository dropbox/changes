from changes.api.serializer import Serializer, register
from changes.models import Task


@register(Task)
class TaskSerializer(Serializer):
    def serialize(self, instance, attrs):
        return {
            'id': instance.id.hex,
            'objectID': instance.task_id,
            'parentObjectID': instance.parent_id,
            'name': instance.task_name,
            'args': instance.data.get('kwargs') or {},
            'attempts': instance.num_retries + 1,
            'status': instance.status,
            'result': instance.result,
            'dateCreated': instance.date_created,
            'dateStarted': instance.date_started,
            'dateFinished': instance.date_finished,
            'dateModified': instance.date_modified,
        }
