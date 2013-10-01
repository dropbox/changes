import json
import os.path

from cStringIO import StringIO


class MockedResponse(object):
    # used to mock out KoalityBackend._get_response
    def __init__(self, base_url, fixture_root):
        self.base_url = base_url
        self.fixture_root = fixture_root

    def __call__(self, method, url, **kwargs):
        fixture = self.load_fixture(method, url, **kwargs)
        if fixture is None:
            # TODO:
            raise Exception

        fixture = os.path.join(self.fixture_root, fixture)

        with open(fixture) as fp:
            return json.load(fp)

    def load_fixture(self, method, url, **kwargs):
        return os.path.join(method.upper(), self.url_to_filename(url))

    def url_to_filename(self, url):
        assert url.startswith(self.base_url)
        return url[len(self.base_url) + 1:].strip('/').replace('/', '__') + '.json'


class MockedHTTPConnection(object):
    def __init__(self, *args, **kwargs):
        self.responder = MockedResponse(*args, **kwargs)

    def __call__(self, host, **kwargs):
        """
        Acts as HTTPConnection.__init__
        """
        self._host = host
        self._request = None
        return self

    def request(self, method, path, body=None, headers={}):
        assert self._request is None
        self._request = {
            'method': method,
            'url': 'http://{0}/{1}'.format(self._host, path),
            'data': body,
            'headers': headers,
        }

    def getresponse(self):
        assert self._request is not None
        return StringIO(json.dumps(self.responder(**self._request)))
