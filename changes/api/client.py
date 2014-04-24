from flask import current_app


class APIClient(object):
    """
    An internal API client.

    >>> client = APIClient(version=0)
    >>> response = client.get('/projects/')
    >>> print response.data
    """
    def __init__(self, version):
        self.version = version

    def dispatch(self, url, method, data=None):
        url = '/api/%d/%s' % (self.version, url.lstrip('/'))
        client = current_app.test_client()
        return client.open(url, method, data)

    def delete(self, *args, **kwargs):
        return self.dispatch(method='DELETE', *args, **kwargs)

    def get(self, *args, **kwargs):
        return self.dispatch(method='GET', *args, **kwargs)

    def head(self, *args, **kwargs):
        return self.dispatch(method='HEAD', *args, **kwargs)

    def options(self, *args, **kwargs):
        return self.dispatch(method='OPTIONS', *args, **kwargs)

    def patch(self, *args, **kwargs):
        return self.dispatch(method='PATCH', *args, **kwargs)

    def post(self, *args, **kwargs):
        return self.dispatch(method='POST', *args, **kwargs)

    def put(self, *args, **kwargs):
        return self.dispatch(method='PUT', *args, **kwargs)

api_client = APIClient(version=0)
