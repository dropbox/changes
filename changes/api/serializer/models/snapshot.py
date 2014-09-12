from __future__ import absolute_import

from collections import defaultdict
from sqlalchemy.orm import joinedload

from changes.api.serializer import Serializer, register, serialize
from changes.models import Build, Snapshot, SnapshotImage


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


class SnapshotWithImagesSerializer(SnapshotSerializer):
    def get_attrs(self, item_list):
        image_list = sorted(SnapshotImage.query.filter(
            SnapshotImage.snapshot_id.in_(j.id for j in item_list),
        ), key=lambda x: x.date_created)
        image_map = defaultdict(list)
        for image in image_list:
            image_map[image.snapshot_id].append(serialize(image))

        result = {}
        for item in item_list:
            result[item] = {'images': image_map.get(item.id, [])}

        return result

    def serialize(self, instance, attrs):
        data = super(SnapshotWithImagesSerializer, self).serialize(instance, attrs)
        data['images'] = attrs['images']
        return data
