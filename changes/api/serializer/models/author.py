from changes.api.serializer import Serializer, register
from changes.models.author import Author


@register(Author)
class AuthorSerializer(Serializer):
    def serialize(self, instance, attrs):
        return {
            'id': instance.id.hex,
            'name': instance.name,
            'email': instance.email,
            'dateCreated': instance.date_created,
        }
