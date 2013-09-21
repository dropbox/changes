import requests
import tornado.web

from collections import defaultdict

KOALITY_URL = 'https://build.itc.dropbox.com'
KOALITY_API_KEY = 'he8i7mxdzrocn6rg9qv852occkvpih9b'

STATUS_QUEUED = 'queued'
STATUS_INPROGRESS = 'in progress'
STATUS_FAILED = 'failed'
STATUS_PASSED = 'passed'


class AttrDict(dict):
    def __getattr__(self, name):
        return self[name]


class BuildDetailsHandler(tornado.web.RequestHandler):
    def get(self, project_id, build_id):
        def get_duration(start_time, end_time):
            if start_time and end_time:
                duration = end_time - start_time
            else:
                duration = None
            return duration

        # {u'branch': u'verify only (api)', u'number': 760, u'createTime': 1379712159000, u'headCommit': {u'sha': u'257e20ba86c5fe1ff1e1f44613a2590bb56d7285', u'message': u'Change format of mobile gandalf info\n\nSummary: Made it more prettier\n\nTest Plan: tried it with my emulator, it works\n\nReviewers: fta\n\nReviewed By: fta\n\nCC: Reviews-Aloha, Server-Reviews\n\nDifferential Revision: https://tails.corp.dropbox.com/D23207'}, u'user': {u'lastName': u'Verifier', u'id': 3, u'firstName': u'Koality', u'email': u'verify-koala@koalitycode.com'}, u'startTime': 1379712161000, u'mergeStatus': None, u'endTime': 1379712870000, u'id': 814}
        change = requests.get('{base_uri}/api/v/0/repositories/{project_id}/changes/{build_id}'.format(
            base_uri=KOALITY_URL, project_id=project_id, build_id=build_id
        ), params={'key': KOALITY_API_KEY}).json()

        # [{u'status': u'passed', u'type': u'compile', u'id': 18421, u'name': u'sudo -H -u lt3 ci/compile'}, {u'status': u'passed', u'type': u'compile', u'id': 18427, u'name': u'sudo ln -svf /usr/local/encap/python-2.7.4.1/bin/tox /usr/local/bin/tox'}, {u'status': u'passed', u'type': u'compile', u'id': 18426, u'name': u'sudo pip install tox'}, {u'status': u'passed', u'type': u'setup', u'id': 18408, u'name': u'hg'}, {u'status': u'passed', u'type': u'setup', u'id': 18409, u'name': u'provision'}, {u'status': u'passed', u'type': u'test', u'id': 18428, u'name': u'blockserver'}, {u'status': u'passed', u'type': u'test', u'id': 18429, u'name': u'dropbox'}, {u'status': u'passed', u'type': u'compile', u'id': 18422, u'name': u'sudo -H -u lt3 ci/compile'}, {u'status': u'passed', u'type': u'compile', u'id': 18431, u'name': u'sudo ln -svf /usr/local/encap/python-2.7.4.1/bin/tox /usr/local/bin/tox'}, {u'status': u'passed', u'type': u'compile', u'id': 18430, u'name': u'sudo pip install tox'}, {u'status': u'passed', u'type': u'setup', u'id': 18406, u'name': u'hg'}, {u'status': u'passed', u'type': u'setup', u'id': 18412, u'name': u'provision'}, {u'status': u'passed', u'type': u'test', u'id': 18432, u'name': u'magicpocket'}, {u'status': u'passed', u'type': u'compile', u'id': 18433, u'name': u'sudo -H -u lt3 ci/compile'}, {u'status': u'passed', u'type': u'compile', u'id': 18441, u'name': u'sudo ln -svf /usr/local/encap/python-2.7.4.1/bin/tox /usr/local/bin/tox'}, {u'status': u'passed', u'type': u'compile', u'id': 18437, u'name': u'sudo pip install tox'}, {u'status': u'passed', u'type': u'setup', u'id': 18407, u'name': u'hg'}, {u'status': u'passed', u'type': u'setup', u'id': 18411, u'name': u'provision'}, {u'status': u'passed', u'type': u'compile', u'id': 18420, u'name': u'sudo -H -u lt3 ci/compile'}, {u'status': u'passed', u'type': u'compile', u'id': 18424, u'name': u'sudo ln -svf /usr/local/encap/python-2.7.4.1/bin/tox /usr/local/bin/tox'}, {u'status': u'passed', u'type': u'compile', u'id': 18423, u'name': u'sudo pip install tox'}, {u'status': u'passed', u'type': u'setup', u'id': 18405, u'name': u'hg'}, {u'status': u'passed', u'type': u'setup', u'id': 18410, u'name': u'provision'}, {u'status': u'passed', u'type': u'test', u'id': 18425, u'name': u'metaserver'}]
        stages = requests.get('{base_uri}/api/v/0/repositories/{project_id}/changes/{build_id}/stages'.format(
            base_uri=KOALITY_URL, project_id=project_id, build_id=build_id
        ), params={'key': KOALITY_API_KEY}).json()

        # for stage in (s for s in stages if s['status'] == 'failed'):

        if change['startTime'] > 0 < change['endTime']:
            if all(s['status'] == 'passed' for s in stages):
                status = STATUS_PASSED
            else:
                status = STATUS_FAILED
        elif change['startTime'] > 0:
            status = STATUS_INPROGRESS
        else:
            status = STATUS_QUEUED

        end_time = max(s['endTime'] for s in stages)

        build = AttrDict({
            'sha': change['headCommit']['sha'],
            'name': change['headCommit']['sha'][:12],
            'number': change['number'],
            'link': 'https://build.itc.dropbox.com/repository/26?change=%d' % (change['id'],),
            'startTime': change['startTime'],
            'endTime': end_time,
            'status': status,
            'duration': get_duration(change['startTime'], end_time),
            'message': change['headCommit']['message'],
            'author': AttrDict(change['headCommit']['user']),
            'nodes': frozenset([s['buildNode'] for s in stages]),
        })

        grouped_stages = defaultdict(list)
        for stage in stages:
            grouped_stages[stage['type']].append(AttrDict({
                'name': stage['name'],
                'startTime': stage['startTime'],
                'endTime': stage['endTime'],
                'duration': get_duration(stage['startTime'], stage['endTime']),
                'status': stage['status'],
                'buildNode': stage['buildNode'],
                'link': 'https://build.itc.dropbox.com/repository/26?change=%d&stage=%d' % (change['id'], stage['id']),
            }))

        steps = []
        for step, stage_list in grouped_stages.iteritems():
            stage_list.sort(key=lambda x: x['status'] == 'passed')

            if all(s['status'] == 'passed' for s in stage_list):
                status = 'passed'
            else:
                status = 'failed'

            start_time = min(s['startTime'] for s in stage_list)
            end_time = max(s['endTime'] for s in stage_list)

            steps.append(AttrDict({
                'name': step.title(),
                'startTime': start_time,
                'endTime': end_time,
                'duration': get_duration(start_time, end_time),
                'status': status,
                'stages': stage_list,
                'nodes': frozenset([s['buildNode'] for s in stage_list]),
            }))
        steps.sort(key=lambda x: x['startTime'])

        context = {
            'build': build,
            'steps': steps,
        }

        return self.render("build_details.html", **context)
