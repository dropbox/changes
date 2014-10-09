from __future__ import absolute_import

from collections import defaultdict
from sqlalchemy.orm import joinedload

from changes.api.serializer import Serializer, register, serialize
from changes.config import db
from changes.models import Build, ProjectOption, Snapshot, SnapshotImage


@register(Snapshot)
class SnapshotSerializer(Serializer):
    def get_attrs(self, item_list):
        image_list = sorted(SnapshotImage.query.options(
            joinedload('plan'),
        ).filter(
            SnapshotImage.snapshot_id.in_(j.id for j in item_list),
        ), key=lambda x: x.date_created)
        image_map = defaultdict(list)
        for image in image_list:
            image_map[image.snapshot_id].append(serialize(image))

        active_snapshots = set((
            x[0] for x in db.session.query(
                ProjectOption.value,
            ).filter(
                ProjectOption.project_id.in_(set(s.project_id for s in item_list)),
                ProjectOption.name == 'snapshot.current',
            )
        ))

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
            result[item] = {
                'images': image_map.get(item.id, []),
                'active': item.id.hex in active_snapshots,
                'build': build_map.get(item.build_id),
            }

        return result

    def serialize(self, instance, attrs):
        return {
            'id': instance.id.hex,
            'project': {
                'id': instance.project_id.hex,
            },
            'source': instance.source,
            'status': instance.status,
            'dateCreated': instance.date_created,
            'images': attrs['images'],
            'build': attrs['build'],
            'isActive': attrs['active'],
        }
