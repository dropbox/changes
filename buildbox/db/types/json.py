from sqlalchemy.types import TypeDecorator, Unicode

import json


class JSONEncodedDict(TypeDecorator):
    impl = Unicode

    def process_bind_param(self, value, dialect):
        if value:
            return unicode(json.dumps(value))

        return u'{}'

    def process_result_value(self, value, dialect):
        if value:
            return json.loads(value)

        return {}
