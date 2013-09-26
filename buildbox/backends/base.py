from buildbox.config import db


class BaseBackend(object):
    def __init__(self):
        self.db = db
