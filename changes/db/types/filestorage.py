from __future__ import absolute_import, print_function

import json

from flask import current_app
from sqlalchemy.ext.mutable import Mutable
from sqlalchemy.types import TypeDecorator, Unicode

from changes.utils.imports import import_string


class FileData(Mutable):
    def __init__(self, data=None, storage_options=None):
        if data is None:
            data = {}
        if storage_options is None:
            storage_options = {}

        self.filename = data.get('filename')
        self.storage = data.get('storage', storage_options.pop('storage', None))
        self.storage_options = storage_options

        # XXX(dcramer): this is a fairly hacky way to specify the file storage
        if self.storage is None:
            self.storage = current_app.config['DEFAULT_FILE_STORAGE']

    def __repr__(self):
        return '<%s: filename=%s>' % (type(self).__name__, self.filename)

    def __nonzero__(self):
        return bool(self.filename)

    def get_storage(self):
        storage = import_string(self.storage)
        return storage(**self.storage_options)

    def url_for(self):
        if self.filename is None:
            return
        return self.get_storage().url_for(self.filename)

    def save(self, fp, filename=None, content_type=None):
        if filename:
            self.filename = filename
        elif self.filename is None:
            raise ValueError('Missing filename')

        self.get_storage().save(self.filename, fp, content_type)
        self.changed()

    def get_file(self, offset=None, length=None):
        if self.filename is None:
            raise ValueError('Missing filename')
        return self.get_storage().get_file(self.filename, offset=offset, length=length)

    def get_content_type(self):
        if self.filename is None:
            raise ValueError('Missing filename')
        return self.get_storage().get_content_type(self.filename)

    @classmethod
    def coerce(cls, key, value):
        return value


class FileStorage(TypeDecorator):
    impl = Unicode

    python_type = FileData

    def __init__(self, storage=None, path='',
                 *args, **kwargs):

        super(FileStorage, self).__init__(*args, **kwargs)

        self.storage_options = {
            'storage': storage,
            'path': path,
        }

    def process_bind_param(self, value, dialect):
        if value:
            if isinstance(value, FileData):
                value = {
                    'filename': value.filename,
                    'storage': value.storage,
                }
            return unicode(json.dumps(value))

        return u'{}'

    def process_result_value(self, value, dialect):
        if value:
            return FileData(json.loads(value), self.storage_options)

        return FileData({}, self.storage_options)

FileData.associate_with(FileStorage)
