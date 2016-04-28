from __future__ import absolute_import

import json
import logging
import requests

from datetime import datetime
from flask.ext.restful import reqparse

from changes.api.auth import get_current_user
from changes.api.base import APIView, error
from changes.config import db
from changes.lib import mesos_lib
from changes.models.jobstep import JobStep
from changes.models.node import Node


class NodeStatusAPIView(APIView):
    get_parser = reqparse.RequestParser()
    get_parser.add_argument(
        'toggle',
        type=lambda x: bool(int(x)),
        location='args',
        default=False
    )

    def get(self, node_id):
        node = Node.query.get(node_id)
        jenkins_master = self.get_jenkins_master(node_id)
        if not jenkins_master:
            mesos_master = mesos_lib.get_mesos_master()
            return self.respond_mesos_status(node, mesos_master)
        return self.respond_jenkins_status(node, jenkins_master)

    def post(self, node_id):
        args = self.get_parser.parse_args()
        if not args.toggle:
            return self.get(node_id)

        node = Node.query.get(node_id)
        if node is None:
            return error('Node not found.', ['node_id'], 404)

        if not node.label:
            return error('Node does not contain a label.', ['node_id'], 404)

        user = get_current_user()
        if user is None:
            return error('User is not logged in.', ['user'], 401)

        jenkins_master = self.get_jenkins_master(node_id)
        if not jenkins_master:
            # We are most likely dealing with a Mesos slave here
            node_hostname = node.label.strip()
            mesos_master = mesos_lib.get_mesos_master()
            if not mesos_lib.is_active_slave(mesos_master, node_hostname):
                return error('Node is currently not active on Mesos master', 400)

            try:
                mesos_lib.toggle_node_maintenance_status(mesos_master, node_hostname)
            except Exception as err:
                return error('Unable to toggle offline status of node %s: %s' % (node_hostname, err), http_code=500)
            return self.respond_mesos_status(node, mesos_master)

        toggle_url = '%s/toggleOffline' % (self.get_jenkins_url(jenkins_master, node.label))
        timestamp = datetime.utcnow()
        data = {
            'offlineMessage': '[changes] Disabled by %s at %s' % (user.email, timestamp)
        }
        response = requests.Session().post(toggle_url, data=data, timeout=10)

        if response.status_code != 200:
            logging.warning('Unable to toggle offline status (%s)' % (toggle_url))

        return self.respond_jenkins_status(node, jenkins_master)

    def respond_jenkins_status(self, node, master):
        if node is None:
            return error('Node not found.', ['node_id'], 404)

        context = {}

        # If this is not a Jenkins node, we don't have master and return an empty dict.
        if master and node.label:
            info_url = '%s/api/json' % (self.get_jenkins_url(master, node.label))
            node_info = None
            try:
                response = requests.Session().get(info_url, timeout=10)
                response.raise_for_status()
                node_info = json.loads(response.text)
            except:
                logging.warning('Unable to get node info (%s)', info_url, exc_info=True)

            if node_info and 'temporarilyOffline' in node_info:
                context['offline'] = node_info['temporarilyOffline']

        return self.respond(context, serialize=False)

    def respond_mesos_status(self, node, mesos_master):
        node_hostname = node.label.strip()
        is_active = mesos_lib.is_active_slave(mesos_master, node_hostname)
        if not is_active:
            return {}

        is_maintenanced = mesos_lib.is_node_under_maintenance(mesos_master, node_hostname)
        return {'offline': is_maintenanced}

    def get_jenkins_master(self, node_id):
        jobstep_data = db.session.query(
            JobStep.data
        ).filter(
            JobStep.node_id == node_id,
            # Otherwise NULL date_finished would be first.
            JobStep.date_finished != None  # NOQA
        ).order_by(
            JobStep.date_finished.desc()
        ).limit(1).scalar()

        if jobstep_data and jobstep_data.get('master'):
            return jobstep_data['master']

        return None

    def get_jenkins_url(self, master, label):
        return '%s/computer/%s' % (master, label)
