from __future__ import absolute_import

from fnmatch import fnmatch

import logging
import os


class ArtifactParseError(Exception):
    pass


class ArtifactHandler(object):
    FILENAMES = ()
    logger = logging.getLogger('artifacts')

    def __init__(self, step):
        self.step = step

    @classmethod
    def can_process(cls, filepath):
        """
        Returns True if this handler can process the given artifact.
        """
        for pattern in cls.FILENAMES:
            if fnmatch(os.path.basename(filepath), pattern):
                return True
        return False

    def process(self, fp):
        """
        Process the given artifact.
        """
