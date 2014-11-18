from __future__ import absolute_import

import logging


class ArtifactHandler(object):
    logger = logging.getLogger('artifacts')

    def __init__(self, step):
        self.step = step
