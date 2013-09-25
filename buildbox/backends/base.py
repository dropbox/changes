from buildbox.app import db


class BaseBackend(object):
    def __init__(self):
        self.db = db

    def get_session(self):
        return self.db.get_session()
