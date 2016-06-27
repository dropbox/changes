from __future__ import absolute_import, print_function


class Manager(object):
    def __init__(self, handlers):
        self.handlers = tuple(handlers)

    def can_process(self, artifact_name):
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
                    handler.process(fp, artifact)
                finally:
                    fp.close()
