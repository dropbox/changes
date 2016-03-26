from unittest2 import TestCase
from changes.lib import mesos_lib
from mock import patch


class MaintenanceWindowTestCase(TestCase):
    @patch('time.time')
    def test_not_in_maintenance_window(self, time_mock):
        class Case(object):
            def __init__(self, window, node, node_in_window, timestamp, window_current):
                self.window = window
                self.node = node
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
            time_mock.return_value = case.timestamp
            assert mesos_lib._is_maintenance_window_currently_active(case.window) == case.window_current

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

    @patch('time.time')
    @patch('socket.gethostbyname')
    def test_mark_node_under_maintenance(self, gethostbyname_mock, time_mock):
        time_mock.return_value = 12345

        testcases = [
            {
                # Add new window
                'maint_data': {
                    'windows': [],
                },
                'node': 'ip-172-31-7-92.us-west-2.compute.internal',
                'ip': '172.31.7.92',

                'expected_maint_data': {
                    'windows': [{
                        "machine_ids": [
                            {
                                "hostname": "ip-172-31-7-92.us-west-2.compute.internal", "ip": "172.31.7.92",
                            }
                        ],
                        "unavailability": {
                            "duration": {
                                "nanoseconds": 36000000000000000
                            },
                            "start": {
                                "nanoseconds": 12345000000000
                            }
                        }
                    }],
                },
            },
            {
                # Replace stale window
                'maint_data': {
                    'windows': [{
                        "machine_ids": [
                            {
                                "hostname": "ip-172-31-7-92.us-west-2.compute.internal", "ip": "172.31.7.92",
                            }
                        ],
                        "unavailability": {
                            "duration": {
                                "nanoseconds": 10
                            },
                            "start": {
                                "nanoseconds": 2
                            }
                        }
                    }],
                },
                'node': 'ip-172-31-7-92.us-west-2.compute.internal',
                'ip': '172.31.7.92',

                'expected_maint_data': {
                    'windows': [{
                        "machine_ids": [
                            {
                                "hostname": "ip-172-31-7-92.us-west-2.compute.internal", "ip": "172.31.7.92",
                            }
                        ],
                        "unavailability": {
                            "duration": {
                                "nanoseconds": 36000000000000000
                            },
                            "start": {
                                "nanoseconds": 12345000000000
                            }
                        }
                    }],
                },
            }
        ]

        for tc in testcases:
            gethostbyname_mock.return_value = tc['ip']
            assert tc['expected_maint_data'] == mesos_lib._mark_node_under_maintenance(tc['maint_data'], tc['node'])

    @patch('time.time')
    @patch('socket.gethostbyname')
    def test_mark_node_out_of_maintenance(self, gethostbyname_mock, time_mock):
        time_mock.return_value = 12345

        testcases = [
            {
                # Remove 'windows' field when last window is removed
                'maint_data': {
                    'windows': [{
                        "machine_ids": [
                            {
                                "hostname": "ip-172-31-7-92.us-west-2.compute.internal", "ip": "172.31.7.92",
                            }
                        ],
                        "unavailability": {
                            "duration": {
                                "nanoseconds": 36000000000000000
                            },
                            "start": {
                                "nanoseconds": 12345000000000
                            }
                        }
                    }],
                },
                'node': 'ip-172-31-7-92.us-west-2.compute.internal',
                'ip': '172.31.7.92',

                'expected_maint_data': {},
            },
            {
                # Only remove hostname if other hosts in same window
                'maint_data': {
                    'windows': [{
                        "machine_ids": [
                            {
                                "hostname": "ip-172-31-7-92.us-west-2.compute.internal", "ip": "172.31.7.92",
                                "hostname": "ip-172-31-7-91.us-west-2.compute.internal", "ip": "172.31.7.91",
                            }
                        ],
                        "unavailability": {
                            "duration": {
                                "nanoseconds": 36000000000000000
                            },
                            "start": {
                                "nanoseconds": 12345000000000
                            }
                        }
                    }],
                },
                'node': 'ip-172-31-7-92.us-west-2.compute.internal',
                'ip': '172.31.7.92',

                'expected_maint_data': {
                    'windows': [{
                        "machine_ids": [
                            {
                                "hostname": "ip-172-31-7-91.us-west-2.compute.internal", "ip": "172.31.7.91",
                            }
                        ],
                        "unavailability": {
                            "duration": {
                                "nanoseconds": 36000000000000000
                            },
                            "start": {
                                "nanoseconds": 12345000000000
                            }
                        }
                    }],
                },
            }
        ]

        for tc in testcases:
            gethostbyname_mock.return_value = tc['ip']
            assert tc['expected_maint_data'] == mesos_lib._mark_node_out_of_maintenance(tc['maint_data'], tc['node'])
