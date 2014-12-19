from changes.api.serializer import Serializer, register
from changes.models import Build, ItemStat
from changes.utils.http import build_uri


@register(Build)
class BuildSerializer(Serializer):
    def get_attrs(self, item_list):
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

    def serialize(self, item, attrs):
        if item.project_id:
            avg_build_time = item.project.avg_build_time
        else:
            avg_build_time = None

        target = item.target
        if target is None and item.source and item.source.revision_sha:
            target = item.source.revision_sha[:12]

        return {
            'id': item.id.hex,
            'collection_id': item.collection_id,
            'number': item.number,
            'name': item.label,
            'target': target,
            'result': item.result,
            'status': item.status,
            'project': item.project,
            'cause': item.cause,
            'author': item.author,
            'source': item.source,
            'message': item.message,
            'tags': item.tags or [],
            'duration': item.duration,
            'estimatedDuration': avg_build_time,
            'dateCreated': item.date_created.isoformat(),
            'dateModified': item.date_modified.isoformat() if item.date_modified else None,
            'dateStarted': item.date_started.isoformat() if item.date_started else None,
            'dateFinished': item.date_finished.isoformat() if item.date_finished else None,
            'stats': attrs['stats'],
            'link': build_uri('/projects/{0}/builds/{1}/'.format(
                item.project.slug, item.id.hex)),
        }
