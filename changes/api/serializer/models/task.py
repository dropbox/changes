from changes.api.serializer import Crumbler, register
from changes.models import Task


@register(Task)
class TaskCrumbler(Crumbler):
    def crumble(self, instance, attrs):
        if instance.data:
            args = instance.data.get('kwargs') or {}
        else:
            args = {}

        return {
            'id': instance.id.hex,
            'objectID': instance.task_id,
            'parentObjectID': instance.parent_id,
            'name': instance.task_name,
            'args': args,
            'attempts': instance.num_retries + 1,
            'status': instance.status,
            'result': instance.result,
            'dateCreated': instance.date_created,
            'dateStarted': instance.date_started,
            'dateFinished': instance.date_finished,
            'dateModified': instance.date_modified,
        }
