from flask import request, current_app

from changes.api.base import APIView

from changes.config import statsreporter

import string
import urlparse


class LogClientPerfAPIView(APIView):
    """
    Record client-side statistics to statsd
    TODO: and hive
    """

    def url_to_key(self, url, prefixes=None):
        """
        create a key from a url (relative or absolute.) We want a low
        cardinality of keys, so we get rid of query parameters and uuids.
        """
        prefixes = prefixes if prefixes else []

        path = urlparse.urlparse(url).path
        url_parts = path.split('/')
        key_parts = prefixes[:]
        for part in url_parts:
            part = part.strip()
            if part == '' or part == '0':
                continue
            is_hex = all(c in string.hexdigits for c in part)
            if len(part) > 10 and is_hex:
                # its a uuid or hash
                continue
            key_parts.append(part)
        key = '_'.join(key_parts)
        return key

    def post(self):
        perf_stats = request.get_json(True)

        key_prefix = ['client_perf']
        if current_app.config['DEBUG']:
            key_prefix.append('dev')
        key_prefix.append('initial' if perf_stats['initial'] else 'switch')

        # record total time per page
        page_key_prefix = key_prefix[:]
        page_key_prefix.append('page')
        page_key = self.url_to_key(perf_stats['url'], page_key_prefix)
        page_duration = perf_stats['endTime'] - perf_stats['startTime']
        statsreporter.stats().log_timing(page_key, page_duration)

        # record stats for each api call
        url_key_prefix = key_prefix[:]  # don't append api, already there
        for url, times in perf_stats['apiCalls'].iteritems():
            key = self.url_to_key(url, url_key_prefix)

            start_time = times['startTime'] - perf_stats['startTime']
            # this can happen when we get a 404 from an api endpoint
            if 'endTime' not in times:
                continue
            duration = times['endTime'] - times['startTime']
            statsreporter.stats().log_timing(key, duration)
            statsreporter.stats().set_gauge(key + '_start', start_time)

        return '', 200
