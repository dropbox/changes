from __future__ import absolute_import, division, unicode_literals

from flask_restful.reqparse import RequestParser

from changes.api.base import APIView
from changes.config import db
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

        offset = args.offset
        if offset is not None:
            # ensure we haven't already recorded an offset that could be
            # in this range
            existing_chunk = LogChunk.query.filter(
                LogChunk.source_id == logsource.id,
                offset >= LogChunk.offset,
                offset <= LogChunk.offset + LogChunk.size - 1,
            ).first()
            if existing_chunk is not None:
                # XXX(dcramer); this is more of an error but we make an assumption
                # that this happens because it was already sent
                existing_msg = {"error": "A chunk within the bounds of the given offset is already recorded."}
                return self.respond(existing_msg, status_code=204)
        else:
            offset = db.session.query(
                LogChunk.offset + LogChunk.size,
            ).filter(
                LogChunk.source_id == logsource.id,
            ).order_by(
                LogChunk.offset.desc(),
            ).limit(1).scalar() or 0

        logchunks = []
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
                'id': c.id,
                'offset': c.offset,
                'size': c.size,
            } for c in logchunks]
        })

        return self.respond(context, serialize=False)
