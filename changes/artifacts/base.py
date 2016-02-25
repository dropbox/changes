from __future__ import absolute_import

from fnmatch import fnmatch

import logging
import os

from changes.storage.artifactstore import ARTIFACTSTORE_PREFIX


class ArtifactParseError(Exception):
    pass


class ArtifactHandler(object):
    FILENAMES = ()
    logger = logging.getLogger('artifacts')

    def __init__(self, step):
        self.step = step

    @staticmethod
    def _sanitize_path(artifact_path):
        # artifactstore prefix shouldn't be considered part of the path
        if artifact_path.startswith(ARTIFACTSTORE_PREFIX):
            artifact_path = artifact_path[len(ARTIFACTSTORE_PREFIX):]
        return artifact_path

    @classmethod
    def can_process(cls, filepath):
        """
        Returns True if this handler can process the given artifact.
        """
        filepath = ArtifactHandler._sanitize_path(filepath)
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
