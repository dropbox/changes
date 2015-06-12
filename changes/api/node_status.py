from __future__ import absolute_import

import json
import logging
import requests

from datetime import datetime
from flask.ext.restful import reqparse

from changes.api.auth import get_current_user
from changes.api.base import APIView, error
from changes.config import db
from changes.models import JobStep, Node


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
        master = self.get_master(node_id)
        return self.respond_status(node, master)

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

        master = self.get_master(node_id)
        if not master:
            return error('Node master not found.', ['node_id'], 404)

        toggle_url = '%s/toggleOffline' % (self.get_jenkins_url(master, node.label))
        timestamp = datetime.utcnow()
        data = {
            'offlineMessage': '[changes] Disabled by %s at %s' % (user.email, timestamp)
        }
        response = requests.Session().post(toggle_url, data=data)

        if response.status_code != 200:
            logging.warning('Unable to toggle offline status (%s)' % (toggle_url))

        return self.respond_status(node, master)

    def respond_status(self, node, master):
        if node is None:
            return error('Node not found.', ['node_id'], 404)

        context = {}

        # If this is not a Jenkins node, we don't have master and return an empty dict.
        if master and node.label:
            info_url = '%s/api/json' % (self.get_jenkins_url(master, node.label))
            response = requests.Session().get(info_url)

            if response.status_code == 200:
                node_info = json.loads(response.text)
                if 'temporarilyOffline' in node_info:
                    context['offline'] = node_info['temporarilyOffline']
            else:
                logging.warning('Unable to get node info (%s)' % (info_url))

        return self.respond(context, serialize=False)

    def get_master(self, node_id):
        jobstep_data = db.session.query(
            JobStep.data
        ).filter(
            JobStep.node_id == node_id
        ).order_by(
            JobStep.date_finished.desc()
        ).limit(1).scalar()

        if jobstep_data and jobstep_data['master']:
            return jobstep_data['master']

        return None

    def get_jenkins_url(self, master, label):
        return '%s/computer/%s' % (master, label)
