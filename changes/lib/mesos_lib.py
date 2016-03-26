"""
Utilities to discover and interact with Mesos master instances
"""

from flask import current_app
from kazoo.client import KazooClient
from requests.exceptions import ConnectionError, HTTPError, Timeout

import json
import requests
import socket
import time

MESOS_REQUEST_TIMEOUT_SECS = 5
SCHEDULE_ENDPOINT = 'master/maintenance/schedule'
STATE_ENDPOINT = 'state.json'
THOUSAND_HOURS_IN_NSEC = 1000 * 3600 * 10e9


def get_mesos_master():
    """
    Discover location of Mesos master instance

    Returns:
        (ip, port) of current Mesos master leader, None otherwise
    """
    zkClient = KazooClient(hosts=current_app.config['ZOOKEEPER_HOSTS'], read_only=True)
    zkClient.start()

    LEADER_PREFIX = current_app.config['ZOOKEEPER_MESOS_MASTER_PATH']

    # Mesos master information is stored in keys like /namespace/json.info_0000001234,
    # /namespace/json.info_0000001345. Object with smallest suffix denotes current leader.
    #
    # Value stored at this key will be a JSON object of the form:
    # {
    #     "address": {
    #         "hostname": "45fa5335c0db",
    #         "ip": "10.1.4.3",
    #         "port": 5050
    #     },
    #     "hostname": "45fa5335c0db",
    #     "id": "5749a9a7-447b-47d5-950f-131b13b0b15f",
    #     "ip": 50594058,
    #     "pid": "master@10.1.4.3:5050",
    #     "port": 5050,
    #     "version": "0.27.0"
    # }

    all_mesos_masters = [child for child in zkClient.get_children(LEADER_PREFIX) if child.startswith('json.info_')]
    # No mesos masters available
    if len(all_mesos_masters) == 0:
        return None

    leader_zk_item = sorted(all_mesos_masters)[0]
    leader_json, _ = zkClient.get(LEADER_PREFIX + '/' + leader_zk_item)
    leader = json.loads(leader_json)

    zkClient.stop()

    return (leader['address']['ip'], leader['address']['port'])


def _master_api_request(master, endpoint, post_data=None):
    ip, port = master
    try:
        url = 'http://%s:%s/%s' % (ip, port, endpoint)
        if post_data:
            return requests.post(url, data=post_data, timeout=MESOS_REQUEST_TIMEOUT_SECS)
        return requests.get(url, timeout=MESOS_REQUEST_TIMEOUT_SECS)
    except (ConnectionError, HTTPError, Timeout) as err:
        # Potentially transient network errors - don't crash Changes
        current_app.logger.warning('Network error during mesos master request (%s): %s', url, err, exc_info=True)
        return []


def _get_slaves(master):
    """
    List slaves associated with a mesos master instance
    """
    state = _master_api_request(master, STATE_ENDPOINT).json()
    return state['slaves']


def _load_maintenance_schedule(master):
    """
    Load maintenance schedule from a Mesos master
    """
    return _master_api_request(master, SCHEDULE_ENDPOINT).json()


def _update_maintenance_schedule(master, maint_data):
    """
    Overwrite maintenance schedule on a Mesos master
    """
    _master_api_request(master, SCHEDULE_ENDPOINT, post_data=json.dumps(maint_data))


def is_active_slave(master, node):
    """
    Check if a node is registered as an active slave on a Mesos master
    """
    slaves = _get_slaves(master)
    for slave in slaves:
        if slave['hostname'] == node:
            return slave['active']

    return False


def _is_node_in_maintenance_window(window, node):
    for maintenanced_node in window['machine_ids']:
        if node == maintenanced_node['hostname']:
            return True

    return False


def _is_maintenance_window_currently_active(window):
    now = time.time()
    unavailability_start = window['unavailability']['start']['nanoseconds']
    unavailability_duration = window['unavailability']['duration']['nanoseconds']

    start_time = unavailability_start / 1e9
    end_time = (unavailability_start + unavailability_duration) / 1e9

    return now >= start_time and now < end_time


def _is_stale_window(window):
    now = time.time()
    unavailability_start = window['unavailability']['start']['nanoseconds']
    unavailability_duration = window['unavailability']['duration']['nanoseconds']

    end_time = (unavailability_start + unavailability_duration) / 1e9

    return now >= end_time


def _remove_node_from_window(window, node):
    filtered_machine_ids = [mnode for mnode in window['machine_ids'] if node != mnode['hostname']]
    if len(filtered_machine_ids) == 0:
        return None

    window['machine_ids'] = filtered_machine_ids
    return window


def _is_node_under_maintenance(maint_data, node):
    if 'windows' in maint_data:
        for window in maint_data['windows']:
            if _is_node_in_maintenance_window(window, node) and _is_maintenance_window_currently_active(window):
                return True

    return False


def _mark_node_under_maintenance(maint_data, node):
    if 'windows' not in maint_data:
        maint_data['windows'] = []

    # Remove stale windows: this is necessary to ensure that the same node is not part of multiple
    # maintenance windows.
    maint_data['windows'] = [window for window in maint_data['windows'] if not _is_stale_window(window)]

    maint_data['windows'].append({
        "machine_ids": [
            {
                "hostname": node,
                "ip": socket.gethostbyname(node),
            }
        ],
        "unavailability": {
            "start": {
                "nanoseconds": int(time.time() * 1e9),
            },
            "duration": {
                "nanoseconds": int(THOUSAND_HOURS_IN_NSEC),
            }
        }})

    return maint_data


def _mark_node_out_of_maintenance(maint_data, node):
    if 'windows' not in maint_data:
        raise 'Node %s is not currently under maintenance' % (node)

    # Remove stale windows
    maint_data['windows'] = [window for window in maint_data['windows'] if not _is_stale_window(window)]

    filtered_windows = []
    for window in maint_data['windows']:
        updated_window = _remove_node_from_window(window, node)
        if updated_window:
            filtered_windows.append(updated_window)

    maint_data['windows'] = filtered_windows

    # Mesos master will reject JSON with empty 'windows' list. Remove 'windows' altogether in this
    # case.
    if len(maint_data['windows']) == 0:
        del maint_data['windows']

    return maint_data


def is_node_under_maintenance(master, node):
    maint_data = _load_maintenance_schedule(master)
    return _is_node_under_maintenance(maint_data, node)


def toggle_node_maintenance_status(master, node):
    maint_data = _load_maintenance_schedule(master)
    if _is_node_under_maintenance(maint_data, node):
        maint_data = _mark_node_out_of_maintenance(maint_data, node)
    else:
        maint_data = _mark_node_under_maintenance(maint_data, node)

    _update_maintenance_schedule(master, maint_data)
