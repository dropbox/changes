import json
import re

from changes.testutils import TestCase

from changes.api.base import APIView


class FakePaginationAPIView(APIView):

    def get(self, range_end=50, range_start=0, fake_request=None):
        fake_request = fake_request if fake_request else dict()
        return self.cursor_paginate(
            range(range_start, range_end),
            lambda x: str(x),
            fake_request=fake_request)


class APIClientTest(TestCase):
    """
    Tests for cursor pagination. Things we want to verify:
      TestSimple:
      - Returns one page of results (without parameters)
      - Returns one page when range length < per_page (20, 25 respectively)
      - Return everything when per_page = 0

      TestNavigate:
      - Get first page
      - Get second page from first page after param
      - Get third page from second page after param
      - Get first page from second page before param

      TestLiveUpdate:
      - Use range 10..80 for the following
      - Get first page (10-35)
      - Get second page from after (35-60)
      - Now start using range 0..80
      - Go back a page (10-35)
      - Go back another page (0-25)

      TestBadParam:
      - try to get with after=BLAHBLAH
      - Verify return code 400
    """

    def decode_response(self, response):
        assert int(response.status_code) == 200

        data = json.loads(response.get_data())
        links = [h[1] for h in response.headers if h[0] == 'Link']
        nav_ids = {}
        for l in links:
            after_match = re.search('after=([^>]*)', l)
            before_match = re.search('before=([^>]*)', l)
            if after_match:
                nav_ids['after'] = after_match.group(1)
            if before_match:
                nav_ids['before'] = before_match.group(1)
        return data, nav_ids, links

    def test_simple(self):
        fake_api = FakePaginationAPIView()

        response1 = fake_api.get()
        data, _, __ = self.decode_response(response1)
        assert data == range(25)

        response2 = fake_api.get(20)
        data2, _, __ = self.decode_response(response2)
        assert data2 == range(20)

        response3 = fake_api.get(fake_request={'per_page': 0})
        data3, nav3, _ = self.decode_response(response3)
        assert data3 == range(50)
        assert 'before' not in nav3
        assert 'after' not in nav3

    def test_navigation(self):
        fake_api = FakePaginationAPIView()

        response1 = fake_api.get(60)
        page1, page1_nav, _ = self.decode_response(response1)
        assert page1 == range(25)
        assert 'before' not in page1_nav
        assert 'after' in page1_nav

        response2 = fake_api.get(
            60, fake_request={'after': page1_nav['after']})
        page2, page2_nav, _ = self.decode_response(response2)
        assert page2 == range(25, 50)
        assert 'before' in page2_nav
        assert 'after' in page2_nav

        response3 = fake_api.get(60, fake_request={'after': page2_nav['after']})
        page3, page3_nav, _ = self.decode_response(response3)
        assert page3 == range(50, 60)

        response1_v2 = fake_api.get(60, fake_request={'before': page2_nav['before']})
        page1_v2, page1_v2_nav, _ = self.decode_response(response1_v2)
        assert page1_v2 == range(25)
        assert 'before' not in page1_v2_nav
        assert 'after' in page1_v2_nav

    def test_live_update(self):
        fake_api = FakePaginationAPIView()

        response1 = fake_api.get(80, range_start=10)
        page1, page1_nav, _ = self.decode_response(response1)
        assert page1 == range(10, 35)
        assert 'after' in page1_nav

        response2 = fake_api.get(80, range_start=10, fake_request={'after': page1_nav['after']})
        page2, page2_nav, _ = self.decode_response(response2)
        assert page2 == range(35, 60)
        assert 'before' in page2_nav

        response1_v2 = fake_api.get(
            80, fake_request={'before': page2_nav['before']})
        page1_v2, page1_v2_nav, _ = self.decode_response(response1_v2)
        assert page1_v2 == range(10, 35)
        assert 'before' in page1_v2_nav

        response0 = fake_api.get(
            80, fake_request={'before': page1_v2_nav['before']})
        page0, page0_nav, _ = self.decode_response(response0)
        assert page0 == range(25)
        assert 'before' not in page0_nav

    def test_bad_param(self):
        fake_api = FakePaginationAPIView()

        response = fake_api.get(80, fake_request={'after': 'BLAHBLAH'})
        assert int(response[1]) == 400
