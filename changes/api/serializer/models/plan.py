from changes.api.serializer import Serializer, register
from changes.models import Plan, Step


@register(Plan)
class PlanSerializer(Serializer):
    def serialize(self, instance):
        return {
            'id': instance.id.hex,
            'name': instance.label,
            'steps': list(instance.steps),
            'dateCreated': instance.date_created,
            'dateModified': instance.date_modified,
        }


@register(Step)
class StepSerializer(Serializer):
    def serialize(self, instance):
        return {
            'id': instance.id.hex,
            'name': instance.get_implementation().get_label(),
            'dateCreated': instance.date_created,
        }
