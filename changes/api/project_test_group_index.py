from __future__ import absolute_import, division, unicode_literals

from flask.ext.restful import reqparse

from changes.api.base import APIView
from changes.config import db
from changes.constants import Result, Status
from changes.models import Project, TestCase, Job, Source
from changes.utils.trees import build_tree


class ProjectTestGroupIndexAPIView(APIView):
    parser = reqparse.RequestParser()
    parser.add_argument('parent', type=unicode, location='args')

    def get(self, project_id):
        project = Project.get(project_id)
        if not project:
            return '', 404

        args = self.parser.parse_args()

        latest_job = Job.query.join(
            Source, Source.id == Job.source_id,
        ).filter(
            Source.patch_id == None,  # NOQA
            Job.project_id == project.id,
            Job.result == Result.passed,
            Job.status == Status.finished,
        ).order_by(
            Job.date_created.desc(),
        ).limit(1).first()

        if not latest_job:
            return self.respond([])

        # use the most recent test
        test_list = db.session.query(
            TestCase.name, TestCase.duration
        ).filter(
            TestCase.project_id == project_id,
            TestCase.job_id == latest_job.id,
        )
        if args.parent:
            test_list = test_list.filter(
                TestCase.name.startswith(args.parent),
            )
        test_list = list(test_list)

        if test_list:
            sep = TestCase(name=test_list[0][0]).sep

            groups = build_tree(
                [t[0] for t in test_list],
                sep=sep,
                min_children=2,
                parent=args.parent,
            )

            # try to drill in to avoid a useless singular root folder
            # TODO(dcramer): it's likely there's a much better way to do this
            # while not args.parent and len(groups) == 1:
            #     try_groups = find_trees(
            #         [t[0] for t in test_list],
            #         sep=sep,
            #         min_leaves=2,
            #         parent=groups[0][0],
            #     )
            #     if not try_groups:
            #         break
            #     groups = try_groups

            results = []
            for group in groups:
                num_tests = 0
                total_duration = 0
                for name, duration in test_list:
                    if name == group or name.startswith(group + sep):
                        num_tests += 1
                        total_duration += duration

                if args.parent:
                    name = group[len(args.parent) + len(sep):]
                else:
                    name = group
                data = {
                    'name': name,
                    'path': group,
                    'totalDuration': total_duration,
                    'numTests': num_tests,
                }
                results.append(data)
            results.sort(key=lambda x: x['totalDuration'], reverse=True)

            trail = []
            context = []
            if args.parent:
                for chunk in args.parent.split(sep):
                    context.append(chunk)
                    trail.append({
                        'path': sep.join(context),
                        'name': chunk,
                    })
        else:
            results = []
            trail = []

        data = {
            'groups': results,
            'trail': trail,
        }

        return self.respond(data, serialize=False)
