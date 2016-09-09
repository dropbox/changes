from __future__ import absolute_import

from changes.buildsteps.default import DefaultBuildStep


class LXCBuildStep(DefaultBuildStep):
    """
    Similar to the default build step, except that it runs the client using
    the LXC adapter.
    """
    def can_snapshot(self):
        return True

    def get_label(self):
        return 'Build via Changes Client (LXC)'

    def get_client_adapter(self):
        return 'lxc'

    @classmethod
    def custom_bin_path(cls):
        # This is where we mount custom binaries in the container
        return '/var/changes/input/'

    def get_allocation_params(self, jobstep):
        params = super(LXCBuildStep, self).get_allocation_params(jobstep)
        params['memory'] = str(self.resources['mem'])
        params['cpus'] = str(self.resources['cpus'])
        return params
