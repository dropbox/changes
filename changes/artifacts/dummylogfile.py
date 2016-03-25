from __future__ import absolute_import

from .base import ArtifactHandler


class DummyLogFileHandler(ArtifactHandler):
    """
    Dummy Artifact handler for log files.
    We only fetch artifacts from Jenkins masters if (according to the registered
    ArtifactHandlers) we are interested in the contents.
    For projects using ArtifactStore this works out fine, but for others it means
    that they'll only have reliable access to the contents of artifacts that are processed.

    This handler exists to signal our interest in the contents of *.log files in those cases
    where they won't be available otherwise.
    """
    FILENAMES = ('*.log',)

    def process(self, fp):
        # We don't need to do anything with the file contents.
        pass
