from changes.api.serializer import Crumbler, register
from changes.models.log import LogSource
from flask import current_app


@register(LogSource)
class LogSourceCrumbler(Crumbler):

    def __init__(self, include_step=True):
        self._include_step = include_step

    def crumble(self, instance, attrs):
        url_getter = None
        if instance.in_artifact_store:
            url_getter = ArtifactStoreLogSource(current_app.config)
        else:
            url_getter = ChangesLogSource(current_app.config)

        result = {
            'id': instance.id.hex,
            'job': {
                'id': instance.job_id.hex,
            },
            'name': instance.name,
            'dateCreated': instance.date_created,
            'urls': url_getter.get_urls(instance),
        }
        if self._include_step:
            result['step'] = instance.step
        return result


class LogSourceWithoutStepCrumbler(LogSourceCrumbler):
    """
    Exactly like LogSourceCrumbler, but doesn't include LogSource.step in the result.
    Use this when you already have the JobStep data to avoid doing unnecessary extra work.
    """
    def __init__(self):
        super(LogSourceWithoutStepCrumbler, self).__init__(include_step=False)


class ArtifactStoreLogSource(object):
    """
    Helper class to make sure artifacts store log source urls can be generated.
    """
    def __init__(self, config):
        self.base_url = config.get('ARTIFACTS_SERVER') or ''

    def get_urls(self, logsource):
        raw_url = "{base_url}/buckets/{bucket}/artifacts/{artifact}/content".format(
            base_url=self.base_url,
            bucket=logsource.step_id.hex,
            artifact=logsource.name
        )

        chunked_url = "{base_url}/buckets/{bucket}/artifacts/{artifact}/chunked".format(
            base_url=self.base_url,
            bucket=logsource.step_id.hex,
            artifact=logsource.name
        )

        return [
            {"url": raw_url, "type": "raw"},
            {"url": chunked_url, "type": "chunked", "priority": _logsource_display_priority(logsource)}
        ]


class ChangesLogSource(object):
    """
    Helper class to make sure Changes log source urls can be generated.
    """
    def __init__(self, config):
        self.base_url = config.get('BASE_URI')

    def get_urls(self, logsource):
        raw_url = "{base_url}/api/0/jobs/{job_id}/logs/{log_id}/?raw=1".format(
            base_url=self.base_url,
            job_id=logsource.job_id,
            log_id=logsource.id
        )
        chunked_url = "{base_url}/api/0/jobs/{job_id}/logs/{log_id}/".format(
            base_url=self.base_url,
            job_id=logsource.job_id,
            log_id=logsource.id
        )

        return [
            {"url": raw_url, "type": "raw"},
            {"url": chunked_url, "type": "chunked", "priority": _logsource_display_priority(logsource)}
        ]


def _logsource_display_priority(ls):
    """
    Provides a score for the logsource for deciding what to display as the machine log.
    A higher priority means it is a better choice.

    Args:
        ls (LogSource): The LogSource to score.

    Returns:
        int: The priority.

    """
    priority = 1
    # Prefer AS logs; they're the future, and it's more efficient.
    if ls.in_artifact_store:
        priority += 1
    # We only want to pick an infra log if we don't have other options.
    if ls.is_infrastructural():
        priority -= 2
    return priority
