from __future__ import absolute_import, division, unicode_literals

from flask import Response, request

from changes.api.base import APIView
from changes.models import LogSource, LogChunk


LOG_BATCH_SIZE = 10000  # 10k chars


class BuildLogDetailsAPIView(APIView):
    def get(self, build_id, source_id):
        """
        Return chunks for a LogSource.
        """
        source = LogSource.query.get(source_id)
        if source is None or source.build_id.hex != build_id:
            return Response(status=404)

        offset = request.args.get('offset', -1)

        queryset = LogChunk.query.filter(
            LogChunk.source_id == source.id,
        ).order_by(LogChunk.offset.desc())

        if offset == -1:
            # starting from the end so we need to know total size
            tail = queryset.first()
            if tail is None:
                logchunks = []
            else:
                logchunks = list(queryset.filter(
                    LogChunk.offset >= tail.offset - LOG_BATCH_SIZE,
                    LogChunk.offset <= tail.offset,
                ))
        else:
            logchunks = list(queryset.filter(
                LogChunk.offset >= offset,
                LogChunk.offset <= offset + LOG_BATCH_SIZE,
            ))

        if logchunks:
            logchunks.sort(key=lambda x: x.date_created)

            text = ''.join(l.text for l in logchunks)

            context = {
                'id': source.id.hex,
                'text': text,
                'offset': logchunks[0].offset,
                'size': len(text),
            }

        else:
            context = {
                'id': source.id.hex,
                'text': '',
                'offset': offset,
                'size': 0,
            }

        return self.respond(context)

    def get_stream_channels(self, build_id, source_id):
        source = LogSource.query.get(source_id)
        if source is None or source.build_id.hex != build_id:
            return Response(status=404)

        return ['logsources:{0}'.format(source.id.hex)]
