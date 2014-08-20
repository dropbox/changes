from __future__ import absolute_import

import pytest

from changes.expanders.commands import CommandsExpander
from changes.testutils import TestCase


class CommandsExpanderTest(TestCase):
    def setUp(self):
        super(CommandsExpanderTest, self).setUp()
        self.project = self.create_project()

    def get_expander(self, data):
        return CommandsExpander(self.project, data)

    def test_validate(self):
        with pytest.raises(AssertionError):
            self.get_expander({}).validate()

        self.get_expander({'commands': []}).validate()

    def test_expand(self):
        results = list(self.get_expander({'commands': [
            {'script': 'echo 1'},
            {'script': 'echo 2', 'label': 'foo'}
        ]}).expand(max_executors=10))

        assert len(results) == 2
        assert results[0].label == 'echo 1'
        assert len(results[0].commands) == 1
        assert results[0].commands[0].label == 'echo 1'
        assert results[0].commands[0].script == 'echo 1'

        assert results[1].label == 'foo'
        assert len(results[1].commands) == 1
        assert results[1].commands[0].label == 'foo'
        assert results[1].commands[0].script == 'echo 2'
