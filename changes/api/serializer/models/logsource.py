from changes.api.serializer import Crumbler, register
from changes.models.log import LogSource
from flask import current_app


@register(LogSource)
class LogSourceCrumbler(Crumbler):
    def crumble(self, instance, attrs):
        url_getter = None
        if instance.in_artifact_store:
            url_getter = ArtifactStoreLogSource(current_app.config)
        else:
            url_getter = ChangesLogSource(current_app.config)

        return {
            'id': instance.id.hex,
            'job': {
                'id': instance.job_id.hex,
            },
            'name': instance.name,
            'step': instance.step,
            'dateCreated': instance.date_created,
            'urls': url_getter.get_urls(instance),
        }


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

        return [{"url": raw_url, "type": "raw"}]


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
            {"url": chunked_url, "type": "chunked"}
        ]
