from __future__ import absolute_import, print_function
from changes.storage.artifactstore import ARTIFACTSTORE_PREFIX


class Manager(object):
    def __init__(self, handlers=None):
        self.handlers = handlers or []

    def register(self, cls):
        self.handlers.append(cls)

    def can_process(self, artifact_name):
        # artifactstore prefix shouldn't be considered part of the path
        if artifact_name.startswith(ARTIFACTSTORE_PREFIX):
            artifact_name = artifact_name[len(ARTIFACTSTORE_PREFIX):]
        return any(cls.can_process(artifact_name) for cls in self.handlers)

    def process(self, artifact, fp=None):
        step = artifact.step
        artifact_name = artifact.name
        for cls in self.handlers:
            if cls.can_process(artifact_name):
                if not fp:
                    fp = artifact.file.get_file()
                handler = cls(step)
                try:
                    handler.process(fp)
                finally:
                    fp.close()
