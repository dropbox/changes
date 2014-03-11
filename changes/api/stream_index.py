from __future__ import absolute_import, division, unicode_literals

from flask.ext.restful import reqparse

from changes.api.base import APIView


class StreamIndexAPIView(APIView):
    parser = reqparse.RequestParser()
    parser.add_argument('c', dest='channels', type=str, action='append',
                        location='args')

    def get_stream_channels(self):
        args = self.parser.parse_args()

        return args.channels
