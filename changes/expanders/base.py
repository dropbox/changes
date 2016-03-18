from __future__ import absolute_import

import logging


class Expander(object):
    logger = logging.getLogger('expander')

    def __init__(self, project, data):
        self.project = project
        self.data = data

    def validate(self):
        """
        Validate that the collection phase's data is valid for expansion.
        Raises AssertionError for any problems in the data.
        """
        raise NotImplementedError

    def expand(self, max_executors, **kwargs):
        """
        Yield up to `max_executors` expanded jobsteps to be run, based on the
        collection phase's data.
        """
        raise NotImplementedError

    def default_phase_name(self):
        """
        Returns the phase name to use for the expanded phase, if none is given
        by the user.
        """
        raise NotImplementedError
