from __future__ import absolute_import

from sqlalchemy.orm import joinedload

from changes.api.base import APIView
from changes.models import Build, Job, JobStep, Node


class NodeJobIndexAPIView(APIView):
    def get(self, node_id):
        node = Node.query.get(node_id)
        if node is None:
            return '', 404

        jobs = list(Job.query.join(
            JobStep, JobStep.job_id == Job.id,
        ).filter(
            JobStep.node_id == node.id,
        ).order_by(Job.date_created.desc()))

        build_list = list(Build.query.options(
            joinedload('project'),
            joinedload('author'),
            joinedload('source').joinedload('revision'),
        ).filter(
            Build.id.in_(j.build_id for j in jobs),
        ))
        build_map = dict(
            (b, d) for b, d in zip(build_list, self.serialize(build_list))
        )

        context = []
        for job, data in zip(jobs, self.serialize(jobs)):
            print job, data
            data['build'] = build_map[job.build]
            context.append(data)

        return self.paginate(context, serialize=False)
