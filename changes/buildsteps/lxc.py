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
