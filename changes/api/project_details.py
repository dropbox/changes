from flask import Response, request
from sqlalchemy.orm import joinedload, subqueryload_all

from changes.api.base import APIView
from changes.config import db
from changes.models import Project, Plan, Build, Source, Status


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


class ProjectValidator(Validator):
    fields = (
        'name',
        'slug',
    )


class ProjectDetailsAPIView(APIView):
    def _get_project(self, project_id):
        project = Project.query.options(
            joinedload(Project.repository),
        ).filter_by(slug=project_id).first()
        if project is None:
            project = Project.query.options(
                joinedload(Project.repository),
            ).get(project_id)
        return project

    def get(self, project_id):
        project = self._get_project(project_id)
        if project is None:
            return Response(status=404)

        plans = Plan.query.options(
            subqueryload_all(Plan.steps),
        ).filter(
            Plan.projects.contains(project),
        )

        data = self.serialize(project)
        data['lastBuild'] = Build.query.options(
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
        data['repository'] = self.serialize(project.repository)
        data['plans'] = self.serialize(list(plans))

        return self.respond(data)

    def post(self, project_id):
        project = self._get_project(project_id)
        if project is None:
            return Response(status=404)

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
            return Response(status=400)

        project.name = result['name']
        project.slug = result['slug']
        db.session.add(project)

        return self.respond(project)
