import json
import os.path


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
