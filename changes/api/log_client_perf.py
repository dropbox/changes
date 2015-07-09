from flask import request

from changes.api.base import APIView

from changes.config import statsreporter

import string
import urlparse


class LogClientPerfAPIView(APIView):
    """
    Record client-side statistics to statsd
    """

    def make_fuzzy_url(self, url):
        """
        If we tried to log a perf key for every unique url, they'd be useless.
        This slightly-sketchy function deletes uuids/hashes and query params
        from the url, and joins together the remaining path parts with _.
        e.g. /api/0/project/changes/commit/134deadbeef -> project_changes_commit
        """
        path = urlparse.urlparse(url).path
        url_parts = path.split('/')
        fuzzy_parts = []
        for part in url_parts:
            part = part.strip()
            if part == '' or part == '0' or part == 'api':
                continue
            is_hex = all(c in string.hexdigits for c in part.replace('-', ''))
            if len(part) > 10 and is_hex:
                # its a uuid or hash
                continue
            fuzzy_parts.append(part)
        return '_'.join(fuzzy_parts)

    def post(self):
        perf_stats = request.get_json(True)
        self.log_page_perf(perf_stats)
        self.log_api_perf(perf_stats)
        return '', 200

    def log_page_perf(self, perf_stats):
        page_load = 'full' if perf_stats['fullPageLoad'] else 'ajax'
        key = "changes_page_perf_load_{}_name_{}".format(
            page_load,
            self.make_fuzzy_url(perf_stats['url']))
        statsreporter.stats().log_timing(
            key,
            perf_stats['endTime'] - perf_stats['startTime'])

    def log_api_perf(self, perf_stats):
        api_key = "changes_api_client_perf_method_{}_class_{}"
        for _, api_data in perf_stats['apiCalls'].iteritems():
            # this can happen when we get a 404 from an api endpoint
            if 'endTime' not in api_data:
                continue
            duration = api_data['endTime'] - api_data['startTime']
            statsreporter.stats().log_timing(
                api_key.format(api_data['apiMethod'], api_data['apiName']),
                duration)
