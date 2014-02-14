from flask import request
from sqlalchemy.orm import joinedload, subqueryload_all

from changes.api.base import APIView
from changes.config import db
from changes.models import (
    Project, Plan, Build, Source, Status, Result, ProjectOption
)


class ValidationError(Exception):
    pass


class Validator(object):
    fields = ()

    def __init__(self, data=None, initial=None):
        self.data = data or {}
        self.initial = initial or {}

    def clean(self):
        result = {}
        for name in self.fields:
            value = self.data.get(name, self.initial.get(name))
            if isinstance(value, basestring):
                value = value.strip()
            result[name] = value

        for key, value in result.iteritems():
            if not value:
                raise ValidationError('%s is required' % (key,))

        return result

OPTION_DEFAULTS = {
    'green-build.notify': '0',
    'green-build.project': '',
    'mail.notify-author': '1',
    'mail.notify-addresses': '',
    'mail.notify-addresses-revisions': '',
    'build.allow-patches': '1',
}


class ProjectValidator(Validator):
    fields = (
        'name',
        'slug',
    )


class ProjectDetailsAPIView(APIView):
    def get(self, project_id):
        project = Project.get(project_id)
        if project is None:
            return '', 404

        plans = Plan.query.options(
            subqueryload_all(Plan.steps),
        ).filter(
            Plan.projects.contains(project),
        )

        last_build = Build.query.options(
            joinedload(Build.author),
        ).join(
            Source, Build.source_id == Source.id,
        ).filter(
            Source.patch_id == None,  # NOQA
            Build.project == project,
            Build.status == Status.finished,
        ).order_by(
            Build.date_created.desc(),
        ).first()
        if not last_build or last_build.result == Result.passed:
            last_passing_build = last_build
        else:
            last_passing_build = Build.query.options(
                joinedload(Build.author),
            ).join(
                Source, Build.source_id == Source.id,
            ).filter(
                Source.patch_id == None,  # NOQA
                Build.project == project,
                Build.result == Result.passed,
                Build.status == Status.finished,
            ).order_by(
                Build.date_created.desc(),
            ).first()

        options = dict(
            (o.name, o.value) for o in ProjectOption.query.filter(
                ProjectOption.project_id == project.id,
            )
        )
        for key, value in OPTION_DEFAULTS.iteritems():
            options.setdefault(key, value)

        data = self.serialize(project)
        data['lastBuild'] = last_build
        data['lastPassingBuild'] = last_passing_build
        data['repository'] = project.repository
        data['plans'] = list(plans)
        data['options'] = options

        return self.respond(data)

    def post(self, project_id):
        project = Project.get(project_id)
        if project is None:
            return '', 404

        validator = ProjectValidator(
            data=request.form,
            initial={
                'name': project.name,
                'slug': project.slug,
            },
        )
        try:
            result = validator.clean()
        except ValidationError:
            return '', 400

        project.name = result['name']
        project.slug = result['slug']
        db.session.add(project)

        return self.respond(project)
