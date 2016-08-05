import re
import json
import requests
import logging

from flask import current_app

# The name is a historical relic -- phabricator_listener.py imports this same logger.
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


class PhabricatorClient(object):
    """
    Implements the logic of talking to phabricator. Always call connect first
    """

    def __init__(self):
        self.auth_params = None

    def connect(self, force=False):
        if self.auth_params and not force:
            return True

        self.host = current_app.config.get('PHABRICATOR_API_HOST')
        self.token = current_app.config.get('PHABRICATOR_TOKEN')

        if not all([self.host, self.token]):
            logger.error(
                "Couldn't find phabricator credentials: host: %s token: %s",
                self.host, self.token)
            return False

        # we're connected. Save connection params
        self.auth_params = {
            'token': self.token,
        }

        # Make an API request, to fail out with an exception if auth info is
        # not correct / we cannot connect.
        self.call('conduit.ping', {})

        return True  # Success!

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

    def post(self, method_name, **params):
        """
        Connect and then call method_name with the keyword params.

        This is a shorthand for
          r.connect()
          r.call('a.b', {'k': v})
        """
        if not self.connect():
            raise RuntimeError("Failed to connect -- see logs")
        return self.call(method_name, params)


def post_diff_comment(revision_id, comment, request):
    # This exists mainly for easy mocking in test_phabricator_listener.py.
    request.post('differential.createcomment', revision_id=revision_id, message=comment)


def post_comment(target, message, request=None):
    """
    Post a comment to a diff in Phabricator.

    The target is a Phabricator revision identifier, e.g. 'D12345'.
    """
    try:
        if request is None:
            request = PhabricatorClient()
        if not request.connect():
            # Return quietly if we can't connect.
            return
        logger.info("Posting build results to %s", target)
        revision_id = target[1:]
        post_diff_comment(revision_id, message, request)
    except requests.exceptions.ConnectionError:
        logger.exception("Failed to post to target: %s", target)
