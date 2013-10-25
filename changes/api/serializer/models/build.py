from changes.api.serializer import Serializer, register
from changes.constants import Result, Status
from changes.models.build import Build


@register(Build)
class BuildSerializer(Serializer):
    def serialize(self, instance):
        # TODO(dcramer): this shouldnt be calculated at runtime
        last_5_builds = list(Build.query.filter_by(
            result=Result.passed,
            status=Status.finished,
            project=instance.project,
        ).order_by(Build.date_finished.desc())[:3])

        if last_5_builds:
            avg_build_time = sum(
                b.duration for b in last_5_builds
                if b.duration
            ) / len(last_5_builds)
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

        return {
            'id': instance.id.hex,
            'name': instance.label,
            'result': instance.result,
            'status': instance.status,
            'project': instance.project,
            'cause': instance.cause,
            'author': instance.author,
            'parent_revision': {
                'sha': instance.parent_revision_sha,
            },
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
