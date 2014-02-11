from __future__ import absolute_import


class BuildStep(object):
    def get_label(self):
        raise NotImplementedError

    def execute(self, job):
        """
        Given a new job, execute it (either sync or async), and report the
        results or yield to an update step.
        """
        raise NotImplementedError

    def update(self, job):
        raise NotImplementedError

    def update_step(self, step):
        raise NotImplementedError

    def cancel(self, job):
        raise NotImplementedError
