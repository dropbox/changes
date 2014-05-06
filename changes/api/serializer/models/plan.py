import json

from changes.api.serializer import Serializer, register
from changes.models import Plan, Step


@register(Plan)
class PlanSerializer(Serializer):
    def serialize(self, instance, attrs):
        return {
            'id': instance.id.hex,
            'name': instance.label,
            'steps': list(instance.steps),
            'dateCreated': instance.date_created,
            'dateModified': instance.date_modified,
        }


@register(Step)
class StepSerializer(Serializer):
    def serialize(self, instance, attrs):
        implementation = instance.get_implementation()

        return {
            'id': instance.id.hex,
            'implementation': instance.implementation,
            'order': instance.order,
            'name': implementation.get_label() if implementation else '',
            'data': json.dumps(dict(instance.data)),
            'dateCreated': instance.date_created,
        }
