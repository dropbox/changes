from hashlib import md5
from urllib.parse import urlencode

from changes.api.serializer import Serializer, register
from changes.models import User


def get_gravatar_url(email, size=None, default='mm'):
    gravatar_url = "https://secure.gravatar.com/avatar/%s" % (
        md5(email.lower().encode('utf-8')).hexdigest())

    properties = {}
    if size:
        properties['s'] = str(size)
    if default:
        properties['d'] = default
    if properties:
        gravatar_url += "?" + urlencode(properties)

    return gravatar_url


@register(User)
class UserSerializer(Serializer):
    def serialize(self, instance, attrs):
        return {
            'id': instance.id.hex,
            'isAdmin': instance.is_admin,
            'email': instance.email,
            'avatar': get_gravatar_url(instance.email),
            'dateCreated': instance.date_created,
        }
