from .builder import JenkinsBuilder


class JenkinsGenericBuilder(JenkinsBuilder):
    def __init__(self, *args, **kwargs):
        self.script = kwargs.pop('script')
        super(JenkinsGenericBuilder, self).__init__(*args, **kwargs)

    def get_job_parameters(self, job):
        params = super(JenkinsGenericBuilder, self).get_job_parameters(job)

        project = job.project
        repository = project.repository

        params.extend([
            {'name': 'CHANGES_PID', 'value': project.slug},
            {'name': 'REPO_URL', 'value': repository.url},
            {'name': 'SCRIPT', 'value': self.script},
            {'name': 'REPO_VCS', 'value': repository.backend.name},
        ])

        return params
