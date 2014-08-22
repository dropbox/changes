from sqlalchemy.orm import joinedload

from changes.api.serializer import Serializer, register, serialize
from changes.models import Build, Snapshot


@register(Snapshot)
class SnapshotSerializer(Serializer):
    def serialize(self, instance, attrs):
        if instance.build_id:
            build = {
                'id': instance.build_id.hex,
            }
        else:
            build = None

        return {
            'id': instance.id.hex,
            'project': {
                'id': instance.project_id.hex,
            },
            'source': instance.source,
            'build': build,
            'status': instance.status,
            'dateCreated': instance.date_created,
        }


class SnapshotWithBuildSerializer(SnapshotSerializer):
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
        data = super(SnapshotWithBuildSerializer, self).serialize(instance, attrs)
        data['build'] = attrs['build']
        return data
