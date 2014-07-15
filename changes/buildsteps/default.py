from __future__ import absolute_import

from changes.buildsteps.base import BuildStep


class Command(object):
    def __init__(self, script, path='', artifacts=None, env=None):
        self.script = script
        self.path = path
        self.artifacts = artifacts
        self.env = env


class DefaultBuildStep(BuildStep):
    """
    A build step which relies on the a scheduling framework in addition to the
    Changes client (or some other push source).

    Jobs will get allocated via a polling step that is handled by the external
    scheduling framework. Once allocated a job is expected to begin reporting
    within a given timeout. All results are expected to be pushed via APIs.
    """
    def __init__(self, commands, path='', env=None, artifacts=None, **kwargs):
        command_defaults = {
            'path': path,
            'env': env or {},
            'artifacts': artifacts or [],
        }
        for command in commands:
            for k, v in command_defaults:
                if k not in command:
                    command[k] = v
        self.commands = map(Command, commands)
        super(DefaultBuildStep, self).__init__(**kwargs)

    def get_label(self):
        return 'Build via Changes Client'

    def execute(self, job):
        pass

    def update(self, job):
        pass

    def update_step(self, step):
        """
        Look for allocated JobStep's and re-queue them if elapsed time is
        greater than allocation timeout.
        """
        # TODO(cramer):

    def cancel_step(self, step):
        pass
