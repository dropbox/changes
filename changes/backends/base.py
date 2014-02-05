class UnrecoverableException(Exception):
    pass


class BaseBackend(object):
    def __init__(self, app):
        self.app = app

    def create_job(self, job):
        raise NotImplementedError

    def sync_job(self, job):
        raise NotImplementedError

    def sync_step(self, step):
        raise NotImplementedError

    def cancel_job(self, job):
        raise NotImplementedError

    def cancel_step(self, step):
        raise NotImplementedError
