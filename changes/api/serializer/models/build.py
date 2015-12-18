from changes.api.serializer import Crumbler, register
from changes.models import Build, ItemStat, FailureReason, JobStep
from changes.utils.http import build_uri

from changes.buildfailures import registry

from collections import defaultdict


@register(Build)
class BuildCrumbler(Crumbler):
    def get_extra_attrs_from_db(self, item_list):
        builds_by_id = {build.id: build for build in item_list}

        # grab build stats
        stat_list = ItemStat.query.filter(
            ItemStat.item_id.in_(r.id for r in item_list),
        )
        stats_by_item = {}
        for stat in stat_list:
            stats_by_item.setdefault(stat.item_id, {})
            stats_by_item[stat.item_id][stat.name] = stat.value

        # grab any failures. We don't grab these for replaced JobSteps
        rows = FailureReason.query.join(
            JobStep, JobStep.id == FailureReason.step_id,
        ).filter(
            FailureReason.build_id.in_(builds_by_id.keys()),
            JobStep.replacement_id.is_(None),
        )

        failures = defaultdict(list)
        for row in rows:
            failures[row.build_id].append({
                'id': row.reason,
                'reason': registry[row.reason].get_html_label(builds_by_id[row.build_id]),
                'step_id': row.step_id,
                'job_id': row.job_id,
                'data': dict(row.data or {}),
            })

        # return data to augment
        result = {}
        for item in item_list:
            result[item] = {
                'stats': stats_by_item.get(item.id, {}),
                'failures': failures.get(item.id, [])
            }

        return result

    def crumble(self, item, attrs):
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
            'dateDecided': item.date_decided.isoformat() if item.date_decided else None,
            'stats': attrs['stats'],
            'failures': attrs['failures'],
            'link': build_uri('/projects/{0}/builds/{1}/'.format(
                item.project.slug, item.id.hex)),
        }
