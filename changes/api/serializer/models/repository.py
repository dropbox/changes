from changes.api.serializer import Crumbler, register
from changes.models.repository import Repository, RepositoryBackend
from changes.vcs.git import GitVcs
from changes.vcs.hg import MercurialVcs


DEFAULT_BRANCHES = {
    RepositoryBackend.git: GitVcs.get_default_revision(),
    RepositoryBackend.hg: MercurialVcs.get_default_revision(),
    RepositoryBackend.unknown: ''
}


@register(Repository)
class RepositoryCrumbler(Crumbler):
    def crumble(self, instance, attrs):
        return {
            'id': instance.id.hex,
            'url': instance.url,
            'backend': instance.backend,
            'status': instance.status,
            'dateCreated': instance.date_created,
            'defaultBranch': DEFAULT_BRANCHES[instance.backend],
        }


@register(RepositoryBackend)
class RepositoryBackendCrumbler(Crumbler):
    def crumble(self, instance, attrs):
        return {
            'id': instance.name,
            'name': unicode(instance),
        }
