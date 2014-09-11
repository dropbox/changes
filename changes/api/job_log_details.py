from __future__ import absolute_import, division, unicode_literals

from flask import Response, request

from changes.api.base import APIView
from changes.models import LogSource, LogChunk


LOG_BATCH_SIZE = 50000  # in length of chars


class JobLogDetailsAPIView(APIView):
    def get(self, job_id, source_id):
        """
        Return chunks for a LogSource.
        """
        source = LogSource.query.get(source_id)
        if source is None or source.job_id != job_id:
            return '', 404

        offset = int(request.args.get('offset', -1))
        limit = int(request.args.get('limit', -1))
        raw = request.args.get('raw')

        if raw and limit == -1:
            limit = 0
        elif limit == -1:
            limit = LOG_BATCH_SIZE

        queryset = LogChunk.query.filter(
            LogChunk.source_id == source.id,
        ).order_by(LogChunk.offset.desc())

        if offset == -1:
            # starting from the end so we need to know total size
            tail = queryset.limit(1).first()

            if tail is None:
                logchunks = []
            else:
                if limit:
                    queryset = queryset.filter(
                        (LogChunk.offset + LogChunk.size) >= max(tail.offset + tail.size - limit, 0),
                    )
                logchunks = list(queryset)
        else:
            queryset = queryset.filter(
                LogChunk.offset > offset,
            )
            if limit:
                queryset = queryset.filter(
                    LogChunk.offset <= offset + limit,
                )
            logchunks = list(queryset)

        logchunks.sort(key=lambda x: x.date_created)

        if logchunks:
            next_offset = logchunks[-1].offset + logchunks[-1].size + 1
        else:
            next_offset = offset

        if raw:
            return Response(''.join(l.text for l in logchunks), mimetype='text/plain')

        context = self.serialize({
            'source': source,
            'chunks': logchunks,
            'nextOffset': next_offset,
        })
        context['source']['step'] = self.serialize(source.step)
        if source.step:
            context['source']['step']['phase'] = self.serialize(source.step.phase),

        return self.respond(context, serialize=False)
