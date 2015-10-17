from collections import defaultdict
from changes.api.serializer import Crumbler, register
from changes.models import JobStep, JobPlan


@register(JobStep)
class JobStepCrumbler(Crumbler):

    def get_extra_attrs_from_db(self, item_list):
        result = {}
        job_id_to_steps = defaultdict(list)
        for step in item_list:
            job_id_to_steps[step.job_id].append(step)
        if job_id_to_steps:
            for jobplan in JobPlan.query.filter(JobPlan.job_id.in_(job_id_to_steps.keys())):
                for step in job_id_to_steps[jobplan.job_id]:
                    result[step] = {'jobplan': jobplan}

        # In theory, every JobStep should have a JobPlan, but we don't need to assume that
        # or enforce it in this method, and this method does need to be sure that each
        # step has an entry in result, so we make sure of that here.
        for step in item_list:
            if step not in result:
                result[step] = {'jobplan': None}

        return result

    def crumble(self, instance, attrs):
        jobplan = attrs['jobplan']
        return {
            'id': instance.id.hex,
            'name': instance.label,
            'phase': {
                'id': instance.phase_id.hex,
            },
            'data': dict(instance.data),
            'result': instance.result,
            'status': instance.status,
            'image': jobplan and jobplan.snapshot_image,
            'node': instance.node,
            'duration': instance.duration,
            'replacement_id': instance.replacement_id,
            'dateCreated': instance.date_created,
            'dateStarted': instance.date_started,
            'dateFinished': instance.date_finished,
        }
