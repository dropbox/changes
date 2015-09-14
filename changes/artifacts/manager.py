from __future__ import absolute_import, print_function


class Manager(object):
    def __init__(self):
        self.handlers = []

    def register(self, cls):
        self.handlers.append(cls)

    def process(self, artifact):
        step = artifact.step
        artifact_name = artifact.name
        for cls in self.handlers:
            if cls.can_process(artifact_name):
                handler = cls(step)
                fp = artifact.file.get_file()
                try:
                    handler.process(fp)
                finally:
                    fp.close()
