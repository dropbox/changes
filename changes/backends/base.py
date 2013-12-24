class UnrecoverableException(Exception):
    pass


class BaseBackend(object):
    def __init__(self, app):
        self.app = app

    def create_build(self, build):
        raise NotImplementedError
