from changes.api.serializer import Crumbler, register
from changes.models.project import Project
from changes.utils.http import build_uri


@register(Project)
class ProjectCrumbler(Crumbler):
    def crumble(self, instance, attrs):
        return {
            'id': instance.id.hex,
            'slug': instance.slug,
            'name': instance.name,
            'repository': {
                'id': instance.repository_id,
            },
            'status': instance.status,
            'dateCreated': instance.date_created,
            'link': build_uri('/projects/{0}/'.format(instance.slug)),
        }
