from flask.ext.restful import reqparse

from changes.api.base import APIView, error
from changes.api.build_index import get_repository_by_url
from changes.jobs.sync_repo import sync_repo


class KickSyncRepoAPIView(APIView):
    parser = reqparse.RequestParser()

    """The repository url for the repo
    """
    parser.add_argument(
        'repository', type=get_repository_by_url, required=True)

    def post(self):
        """This endpoint kicks off a sync_repo task asynchronously for
        the given repository url.
        """
        args = self.parser.parse_args()
        if args.repository is None:
            # this is None when the url is not recognized
            return error('Repository url is not recognized.', problems=['repository'])
        # TODO should we worry about DoS? Maybe only start the task if it's not
        # already running?
        sync_repo.delay(repo_id=args.repository.id.hex, continuous=False)
        return ''
