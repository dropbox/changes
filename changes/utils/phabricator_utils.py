import re
import hashlib
import time
import json
import requests
import logging

from flask import current_app

# eh, just use the same logger as the listener code
logger = logging.getLogger('phabricator-listener')

# Functions to locally recognize/parse diffusion ids

DIFFUSION_REGEX = re.compile(r'^r[A-Z]+([a-z0-9]+)$')


def might_be_diffusion_iden(text):
    """
    guesses whether text is a diffusion commit name. Right now, it just
    checks the following:
      - starts with lowercase r
      - followed by UPPERCASE CHARACTERS
      - followed by lowercase letters and/or numbers
    Example: rREPOda63b27b7bbd1

    Params:
        text (str): the string to test

    Returns:
        bool: true if its probably a diffusion identifier
    """
    return DIFFUSION_REGEX.match(text) is not None


def get_hash_from_diffusion_iden(text):
    """
    Given a string that's very likely a diffusion identifier (see
    might_be_diffusion_iden() above), extract its commit hash/number.

    Params:
        text (str): the diffusion identifier

    Returns:
        str: the commit hash portion of the identifier, or None if the function
        wasn't able to extract it
    """
    match = DIFFUSION_REGEX.match(text)
    if match is None:
        return None
    return match.group(1)


class PhabricatorRequest:
    """
    Implements the logic of talking to phabricator. Always call connect first
    """

    def __init__(self):
        self.auth_params = None

    def connect(self, force=False):
        if self.auth_params and not force:
            raise RuntimeError("already connected to phabricator!")

        self.user = current_app.config.get('PHABRICATOR_USERNAME')
        self.host = current_app.config.get('PHABRICATOR_HOST')
        self.cert = current_app.config.get('PHABRICATOR_CERT')

        if not self.cert:
            logger.error(
                "Couldn't find phabricator credentials user: %s host: %s cert: %s",
                self.user, self.host, self.cert)
            return

        token = int(time.time())

        connect_args = {
            'authSignature': hashlib.sha1(str(token) + self.cert).hexdigest(),
            'authToken': token,
            'client': 'changes',
            'clientDescription': 'conduit calls from changes api server',
            'clientVersion': 1,
            'host': self.host,
            'user': self.user,
        }

        connect_url = "%s/api/conduit.connect" % self.host
        resp = requests.post(connect_url, {
            '__conduit__': True,
            'output': 'json',
            'params': json.dumps(connect_args),
        }, timeout=10)
        resp.raise_for_status()

        resp = json.loads(resp.content)['result']

        # we're connected. Save connection params
        self.auth_params = {
            'connectionID': resp['connectionID'],
            'sessionKey': resp['sessionKey'],
        }

    def call(self, method_name, params):
        if '__conduit__' in params:
            raise ValueError('phabricator params should not have __conduit__!')

        if not self.auth_params:
            raise RuntimeError('not connected to phabricator')

        params['__conduit__'] = self.auth_params
        args = {
            'params': json.dumps(params),
            'output': 'json',
        }

        url = "%s/api/%s" % (self.host, method_name)

        resp = requests.post(url, args, timeout=10)
        resp.raise_for_status()

        content = json.loads(resp.content)
        if content.get('error_code'):  # always present, but may be null
            raise ValueError((content['error_code'], content['error_info']))

        return content['result']
