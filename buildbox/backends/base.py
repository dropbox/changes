from buildbox.db.backend import Backend


class BaseBackend(object):
    def __init__(self):
        self.backend = Backend.instance()

    def get_session(self):
        return self.backend.get_session()
