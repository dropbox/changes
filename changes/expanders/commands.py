from __future__ import absolute_import

from changes.expanders.base import Expander
from changes.models import FutureCommand, FutureJobStep


class CommandsExpander(Expander):
    """
    The ``commands`` value must exist and be valid command parameters:

        {
            "phase": "optional phase name",
            "commands": [
                {"name": "Optional name",
                 "script": "echo 1"},
                {"script": "py.test --junit=junit.xml"}
            ]
        }
    """
    def validate(self):
        assert 'commands' in self.data, 'Missing ``commands`` attribute'

    def expand(self, max_executors, **kwargs):
        for cmd_data in self.data['commands']:
            # TODO: group commands with jobsteps so as to respect max_executors
            future_command = FutureCommand(**cmd_data)
            future_jobstep = FutureJobStep(
                label=cmd_data.get('label') or future_command.label,
                commands=[future_command],
            )
            yield future_jobstep
