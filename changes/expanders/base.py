from __future__ import absolute_import

import logging


class Expander(object):
    logger = logging.getLogger('expander')

    def __init__(self, project, data):
        self.project = project
        self.data = data

    def validate(self):
        raise NotImplementedError

    def expand(self, max_executors, **kwargs):
        raise NotImplementedError
