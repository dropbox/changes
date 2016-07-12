import unittest
import uuid
import mock

from changes.utils.http import build_patch_uri


class TestBuildPatchUri(unittest.TestCase):
    def test_internal(self):
        patch_id = uuid.UUID('ee62b37b-bc3f-4efe-83bc-f75152d60405')
        app = mock.Mock(config={'INTERNAL_BASE_URI': 'https://base_uri/'})
        uri = build_patch_uri(patch_id, app)
        assert uri == 'https://base_uri/api/0/patches/{0}/?raw=1'.format(
            patch_id.hex)

    def test_use_patch(self):
        patch_id = uuid.UUID('ee62b37b-bc3f-4efe-83bc-f75152d60405')
        app = mock.Mock(config={
            'INTERNAL_BASE_URI': 'https://base_uri/',
            'PATCH_BASE_URI': 'https://patch_uri/'
        })
        uri = build_patch_uri(patch_id, app)
        assert uri == 'https://patch_uri/api/0/patches/{0}/?raw=1'.format(
            patch_id.hex)
