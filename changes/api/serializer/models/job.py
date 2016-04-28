from sqlalchemy.orm import joinedload

from changes.api.serializer import Crumbler, register, serialize
from changes.models.build import Build
from changes.models.itemstat import ItemStat
from changes.models.job import Job


@register(Job)
class JobCrumbler(Crumbler):
    def get_extra_attrs_from_db(self, item_list):
        stat_list = ItemStat.query.filter(
            ItemStat.item_id.in_(r.id for r in item_list),
        )
        stats_by_item = {}
        for stat in stat_list:
            stats_by_item.setdefault(stat.item_id, {})
            stats_by_item[stat.item_id][stat.name] = stat.value

        result = {}
        for item in item_list:
            result[item] = {'stats': stats_by_item.get(item.id, {})}

        return result

    def crumble(self, instance, attrs):
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
            'stats': attrs['stats'],
            'dateCreated': instance.date_created.isoformat(),
            'dateModified': instance.date_modified.isoformat() if instance.date_modified else None,
            'dateStarted': instance.date_started.isoformat() if instance.date_started else None,
            'dateFinished': instance.date_finished.isoformat() if instance.date_finished else None,
        }
        if instance.build_id:
            data['build'] = {'id': instance.build_id.hex}
        return data


class JobWithBuildCrumbler(JobCrumbler):
    def get_extra_attrs_from_db(self, item_list):
        result = super(JobWithBuildCrumbler, self).get_extra_attrs_from_db(item_list)

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

        for item in item_list:
            result[item]['build'] = build_map.get(item.build_id)

        return result

    def crumble(self, instance, attrs):
        data = super(JobWithBuildCrumbler, self).crumble(instance, attrs)
        # TODO(dcramer): this is O(N) queries due to the attach helpers
        data['build'] = attrs['build']
        return data
