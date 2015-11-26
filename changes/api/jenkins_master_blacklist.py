from __future__ import absolute_import

from flask.ext.restful import reqparse

from changes.api.base import APIView
from changes.backends.jenkins.builder import MASTER_BLACKLIST_KEY
from changes.config import redis


class JenkinsMasterBlacklistAPIView(APIView):
    """Endpoint for managing the Jenkins master blacklist.

    The blacklist is a set of Jenkins masters that Changes won't give jobs to.
    This is useful for gracefully removing a master temporarily without having
    to modify project configs.
    """

    parser = reqparse.RequestParser()

    """Master url to add or remove from the blacklist."""
    parser.add_argument('master_url', type=str, required=True)

    """Whether to remove from the blacklist instead of add.

    By default, the post adds the master to the blacklist.
    """
    parser.add_argument('remove', type=bool, default=False)

    def post(self):
        """Adds or removes a master from the blacklist.

        The post params should include the `master_url` to be added or removed.
        By default, the master will be added to the blacklist. Set `remove` to
        be true to remove the master.

        Responds with the current blacklist and a warning message if it was a noop.
        """
        args = self.parser.parse_args()

        master = args.master_url
        remove = args.remove

        warning = ''
        if remove:
            if 0 == redis.srem(MASTER_BLACKLIST_KEY, master):
                warning = 'The master was already not on the blacklist'
        else:
            if 0 == redis.sadd(MASTER_BLACKLIST_KEY, master):
                warning = 'The master was already on the blacklist'

        response = dict()
        blacklist = list(redis.smembers(MASTER_BLACKLIST_KEY))
        response['blacklist'] = blacklist

        if warning:
            response['warning'] = warning
        return self.respond(response, serialize=True)

    def get(self):
        """Responds with the list of Jenkins masters in the blacklist.
        """
        response = dict()
        blacklist = list(redis.smembers(MASTER_BLACKLIST_KEY))
        response['blacklist'] = blacklist
        return self.respond(response, serialize=True)
