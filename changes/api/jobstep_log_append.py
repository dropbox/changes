from __future__ import absolute_import, division, unicode_literals

from flask_restful.reqparse import RequestParser

from changes.api.base import APIView
from changes.db.utils import create_or_update, get_or_create
from changes.models import JobStep, LogSource, LogChunk, LOG_CHUNK_SIZE
from changes.utils.text import chunked


class JobStepLogAppendAPIView(APIView):
    parser = RequestParser()
    # the label of the LogSource
    parser.add_argument('source', type=unicode, required=True)
    # the offset at which this chunk begins which will also be validated
    # to ensure we haven't already stored it
    parser.add_argument('offset', type=int)
    parser.add_argument('text', required=True)

    def post(self, step_id):
        """
        Create a new LogSource or append to an existing source (by name)
        a given set of chunks.

        Very basic soft checking is done to see if a chunk is already present
        in the database. Of note, it's not guaranteed to be correct as another
        commit could be in progress.
        """
        step = JobStep.query.get(step_id)
        if step is None:
            return '', 404

        args = self.parser.parse_args()

        logsource, _ = get_or_create(LogSource, where={
            'step_id': step.id,
            'name': args.source,
        }, defaults={
            'project_id': step.project_id,
            'job_id': step.job_id,
        })

        if args.offset is not None:
            # ensure we haven't already recorded an offset that could be
            # in this range
            existing_chunk = LogChunk.query.filter(
                LogChunk.source_id == logsource.id,
                args.offset >= LogChunk.offset,
                args.offset <= LogChunk.offset + LogChunk.size - 1,
            ).first()
            if existing_chunk is not None:
                # XXX(dcramer); this is more of an error but we make an assumption
                # that this happens because it was already sent
                # TODO(dcramer): this should really return a different status code
                # but something in Flask/Flask-Restful is causing the test suite
                # to error if we return 204
                existing_msg = {"error": "A chunk within the bounds of the given offset is already recorded."}
                return self.respond(existing_msg, status_code=200)
        else:
            # TODO(dcramer): we should support a straight up simple append
            raise NotImplementedError

        logchunks = []
        offset = args.offset
        for chunk in chunked(args.text, LOG_CHUNK_SIZE):
            chunk_size = len(chunk)
            chunk, _ = create_or_update(LogChunk, where={
                'source': logsource,
                'offset': offset,
            }, values={
                'job': step.job,
                'project': step.project,
                'size': chunk_size,
                'text': chunk,
            })
            offset += chunk_size
            logchunks.append(chunk)

        context = self.serialize({
            'source': logsource,
            'chunks': [{
                'id': chunk.id,
                'offset': chunk.offset,
                'size': chunk.size,
            } for chunk in logchunks]
        })

        return self.respond(context, serialize=False)
