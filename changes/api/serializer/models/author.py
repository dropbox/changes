from changes.api.serializer import Serializer, register
from changes.api.serializer.models.user import get_gravatar_url
from changes.models.author import Author


@register(Author)
class AuthorSerializer(Serializer):
    def serialize(self, instance, attrs):
        return {
            'id': instance.id.hex,
            'name': instance.name,
            'email': instance.email,
            'avatar': get_gravatar_url(instance.email),
            'dateCreated': instance.date_created,
        }
