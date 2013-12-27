from changes.api.serializer import Serializer, register
from changes.models.aggregatetest import AggregateTestGroup
from changes.utils.http import build_uri


@register(AggregateTestGroup)
class AggregateTestGroupSerializer(Serializer):
    def serialize(self, instance):
        if instance.parent:
            short_name = instance.name[len(instance.parent.name) + 1:]
        else:
            short_name = instance.name

        data = {
            'id': instance.id.hex,
            'name': instance.name,
            'shortName': short_name,
            'link': build_uri('/projects/{0}/tests/{1}/'.format(
                instance.project_id.hex,
                instance.id.hex,
            )),
            'dateCreated': instance.date_created,
        }

        if hasattr(instance, 'last_testgroup'):
            data['lastTest'] = instance.last_testgroup
        return data


class AggregateTestGroupWithJobSerializer(AggregateTestGroupSerializer):
    def serialize(self, instance):
        data = super(AggregateTestGroupWithJobSerializer, self).serialize(instance)
        data.update({
            'firstBuild': instance.first_job,
            'lastBuild': instance.last_job,
        })
        return data
