from __future__ import absolute_import

from uuid import UUID
from werkzeug.routing import BaseConverter, ValidationError


class UUIDConverter(BaseConverter):
    """
    UUID converter for the Werkzeug routing system.
    """
    def to_python(self, value):
        try:
            return UUID(value)
        except ValueError:
            raise ValidationError

    def to_url(self, value):
        return str(value)
