from unittest2 import TestCase
from changes.lib import mesos_lib
from collections import namedtuple


class MaintenanceWindowTestCase(TestCase):
    def test_not_in_maintenance_window(self):
        class Case(object):
            def __init__(self, window, node, node_in_window, timestamp, window_current):
                self.window = window
                self.node = namedtuple('Node', 'label')
                self.node.label = node
                self.node_in_window = node_in_window
                self.timestamp = timestamp
                self.window_current = window_current

        test_cases = [
            Case(window={
                "machine_ids": [
                    {
                        "hostname": "ip-172-31-7-92.us-west-2.compute.internal", "ip": "172.31.7.92",
                    }
                ],
                "unavailability": {
                    "duration": {
                        "nanoseconds": 3600000000000
                    },
                    "start": {
                        "nanoseconds": 1234000000000
                    }
                }
            }, node='ip-172-31-7-92.us-west-2.compute.internal', node_in_window=True, timestamp=1234, window_current=True),

            Case(window={
                "machine_ids": [
                    {
                        "hostname": "ip-172-31-7-92.us-west-2.compute.internal", "ip": "172.31.7.92",
                    }
                ],
                "unavailability": {
                    "duration": {
                        "nanoseconds": 3600000000000
                    },
                    "start": {
                        "nanoseconds": 1234000000000
                    }
                }
            }, node='ip-172-31-7-91.us-west-2.compute.internal', node_in_window=False, timestamp=1232, window_current=False),

            Case(window={
                "machine_ids": [
                    {
                        "hostname": "ip-172-31-7-92.us-west-2.compute.internal", "ip": "172.31.7.92",
                    }
                ],
                "unavailability": {
                    "duration": {
                        "nanoseconds": 3600000000000
                    },
                    "start": {
                        "nanoseconds": 1000000000000
                    }
                }
            }, node='ip-172-31-7-91.us-west-2.compute.internal', node_in_window=False, timestamp=5000, window_current=False)
        ]

        for case in test_cases:
            assert mesos_lib._is_node_in_maintenance_window(case.window, case.node) == case.node_in_window
            assert mesos_lib._is_maintenance_window_currently_active(case.window, now=case.timestamp) == case.window_current

    def test_remove_from_window(self):
        # Remove node if found in window
        assert mesos_lib._remove_node_from_window({
                "machine_ids": [
                    {
                        "hostname": "ip-172-31-7-92.us-west-2.compute.internal", "ip": "172.31.7.92",
                    }
                ],
                "unavailability": {}
        }, "ip-172-31-7-92.us-west-2.compute.internal") is None

        # Don't modify windows which don't contain node
        assert mesos_lib._remove_node_from_window({
                "machine_ids": [
                    {
                        "hostname": "ip-172-31-7-92.us-west-2.compute.internal", "ip": "172.31.7.92",
                    }
                ],
                "unavailability": {}
        }, "ip-172-31-7-91.us-west-2.compute.internal")

        # Don't remove window if at least one node still remains
        assert mesos_lib._remove_node_from_window({
                "machine_ids": [
                    {
                        "hostname": "ip-172-31-7-91.us-west-2.compute.internal", "ip": "172.31.7.91",
                    },
                    {
                        "hostname": "ip-172-31-7-92.us-west-2.compute.internal", "ip": "172.31.7.92",
                    }
                ],
                "unavailability": {}
        }, "ip-172-31-7-91.us-west-2.compute.internal")
