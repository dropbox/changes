from __future__ import absolute_import, division, unicode_literals

from flask import current_app

from changes.api.base import APIView

from changes.utils.phabricator_utils import PhabricatorRequest

import requests


class QuarantineTasksAPIView(APIView):
    def get(self):
        """
        Gets the list of open tasks associated with quarantined tests. We find
        them based on the fact that they're always created by the same
        bot/user.
        """

        try:
            quarantine_user = current_app.config['QUARANTINE_PHID']
            if not quarantine_user:
                return self.respond({
                    'fetched_data_from_phabricator': False
                })

            request = PhabricatorRequest()
            request.connect()
            task_info = request.call('maniphest.query', {'authorPHIDs': [quarantine_user]})

            # we need to get the names of the task owners too
            user_info = {}
            owner_phids = [t['ownerPHID'] for t in task_info.values() if t.get('ownerPHID')]
            if owner_phids:
                user_info = request.call('phid.query', {'phids': owner_phids})

            return self.respond({
                'fetched_data_from_phabricator': True,
                'tasks': task_info,
                'users': user_info
            })

        except requests.exceptions.ConnectionError:
            return 'Unable to connect to Phabricator', 503
