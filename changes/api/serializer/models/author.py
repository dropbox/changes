from changes.api.serializer import Crumbler, register
from changes.api.serializer.models.user import get_gravatar_url
from changes.models.author import Author


@register(Author)
class AuthorCrumbler(Crumbler):
    def crumble(self, instance, attrs):
        return {
            'id': instance.id.hex,
            'name': instance.name,
            'email': instance.email,
            'avatar': get_gravatar_url(instance.email),
            'dateCreated': instance.date_created,
        }
