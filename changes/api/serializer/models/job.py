from sqlalchemy.orm import joinedload

from changes.api.serializer import Serializer, register, serialize
from changes.models import Build, Job


@register(Job)
class JobSerializer(Serializer):
    def serialize(self, instance, attrs):
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

        data = {
            'id': instance.id.hex,
            'number': instance.number,
            'name': instance.label,
            'result': instance.result,
            'status': instance.status,
            'project': instance.project,
            'duration': instance.duration,
            'estimatedDuration': avg_build_time,
            'external': external,
            'dateCreated': instance.date_created.isoformat(),
            'dateModified': instance.date_modified.isoformat() if instance.date_modified else None,
            'dateStarted': instance.date_started.isoformat() if instance.date_started else None,
            'dateFinished': instance.date_finished.isoformat() if instance.date_finished else None,
        }
        if instance.build_id:
            data['build'] = {'id': instance.build_id.hex}
        return data


class JobWithBuildSerializer(JobSerializer):
    def get_attrs(self, item_list):
        build_list = list(Build.query.options(
            joinedload('project'),
            joinedload('author'),
            joinedload('source').joinedload('revision'),
        ).filter(
            Build.id.in_(j.build_id for j in item_list),
        ))
        build_map = dict(
            (b.id, d) for b, d in zip(build_list, serialize(build_list))
        )

        result = {}
        for item in item_list:
            result[item] = {'build': build_map.get(item.build_id)}

        return result

    def serialize(self, instance, attrs):
        data = super(JobWithBuildSerializer, self).serialize(instance, attrs)
        # TODO(dcramer): this is O(N) queries due to the attach helpers
        data['build'] = attrs['build']
        return data
