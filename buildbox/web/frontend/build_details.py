from collections import defaultdict

from buildbox.models import Build, Phase, Step, Author, Revision

from buildbox.web.base_handler import BaseRequestHandler


class BuildDetailsHandler(BaseRequestHandler):
    def get(self, project_id, build_id):
        session = self.db.get_session()

        build = session.query(Build).get(build_id)
        phases = list(session.query(Phase).filter_by(build_id=build.id))
        steps = list(session.query(Step).filter_by(build_id=build.id))

        # TODO: probably a better way to do relations
        revision = session.query(Revision).filter_by(
            sha=build.parent_revision_sha, repository_id=build.repository_id)[0]
        author = session.query(Author).get(revision.author_id)

        steps_by_phase = defaultdict(list)
        for step in steps:
            steps_by_phase[step.phase_id].append(step)

        for phase in phases:
            phase.steps = steps_by_phase[phase.id]

        context = {
            'build': build,
            'revision': revision,
            'author': author,
            'phases': phases,
        }

        return self.render("build_details.html", **context)
