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
            # we take a simplified gitignore-like approach, where if the
            # pattern has a slash in it, we match it against the file path;
            # otherwise we match against the basename.
            if '/' in pattern:
                # ignore starting slash
                if pattern.startswith('/'):
                    pattern = pattern[1:]
                if fnmatch(filepath, pattern):
                    return True
            elif fnmatch(os.path.basename(filepath), pattern):
                return True
        return False

    def process(self, fp):
        """
        Process the given artifact.
        """
