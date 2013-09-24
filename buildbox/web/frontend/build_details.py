from collections import defaultdict

from buildbox.models import (
    Build, Phase, Step, Test, Revision, Author
)

from buildbox.web.base_handler import BaseRequestHandler


class BuildDetailsHandler(BaseRequestHandler):
    def get(self, project_id, build_id):
        with self.db.get_session() as session:
            build = session.query(Build).get(build_id)
            phase_list = list(session.query(Phase).filter_by(build_id=build.id))
            steps = list(session.query(Step).filter_by(build_id=build.id))
            test_list = list(session.query(Test).filter_by(
                build_id=build.id).order_by('-result', '-duration'))

            # TODO: probably a better way to do relations
            revision = session.query(Revision).filter_by(
                sha=build.parent_revision_sha, repository_id=build.repository_id)[0]
            author = session.query(Author).get(revision.author_id)

        steps_by_phase = defaultdict(list)
        for step in steps:
            steps_by_phase[step.phase_id].append(step)

        for phase in phase_list:
            phase.steps = steps_by_phase[phase.id]

        context = {
            'build': build,
            'revision': revision,
            'author': author,
            'phase_list': phase_list,
            'test_list': test_list,
        }

        return self.render("build_details.html", **context)
