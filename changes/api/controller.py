from flask.signals import got_request_exception
from flask.ext.restful import Api, Resource


class APIController(Api):
    def handle_error(self, e):
        """
        Almost identical to Flask-Restful's handle_error, but fixes some minor
        issues.

        Specifically, this fixes exceptions so they get propagated correctly
        when ``propagate_exceptions`` is set.
        """
        if not hasattr(e, 'code') and self.app.propagate_exceptions:
            got_request_exception.send(self.app, exception=e)
            raise

        return super(APIController, self).handle_error(e)


class APICatchall(Resource):
    def get(self, path):
        return {'error': 'Not Found'}, 404

    post = get
    put = get
    delete = get
    patch = get
