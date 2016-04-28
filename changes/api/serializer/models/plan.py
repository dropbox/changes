import json

from changes.api.serializer import Crumbler, register
from changes.models.jobplan import HistoricalImmutableStep
from changes.models.plan import Plan
from changes.models.option import ItemOption
from changes.models.step import Step


@register(Plan)
class PlanCrumbler(Crumbler):
    def crumble(self, instance, attrs):
        return {
            'id': instance.id.hex,
            'project_id': instance.project_id,
            'name': instance.label,
            'steps': list(instance.steps),
            'status': instance.status,
            'dateCreated': instance.date_created,
            'dateModified': instance.date_modified,
        }


@register(Step)
class StepCrumbler(Crumbler):
    def get_extra_attrs_from_db(self, item_list):
        option_list = ItemOption.query.filter(
            ItemOption.item_id.in_(r.id for r in item_list),
        )
        options_by_item = {}
        for option in option_list:
            options_by_item.setdefault(option.item_id, {})
            options_by_item[option.item_id][option.name] = option.value

        result = {}
        for item in item_list:
            result[item] = {'options': options_by_item.get(item.id, {})}

        return result

    def crumble(self, instance, attrs):
        return {
            'id': instance.id.hex,
            'implementation': instance.implementation,
            'name': instance.implementation.rsplit('.', 1)[-1],
            'order': instance.order,
            # 'data' is rendered as JSON string for human reading/editing,
            # so we make it pretty.
            'data': _pretty_json_dump(dict(instance.data or {})),
            'dateCreated': instance.date_created,
            'options': attrs['options'],
        }


@register(HistoricalImmutableStep)
class HistoricalImmutableStepCrumbler(Crumbler):
    def crumble(self, instance, attrs):
        implementation = instance.get_implementation()

        return {
            'id': instance.id.hex,
            'implementation': instance.implementation,
            'name': implementation.get_label() if implementation else '',
            # 'data' is rendered as JSON string for human reading/editing,
            # so we make it pretty.
            'data': _pretty_json_dump(dict(instance.data or {})),
            'options': instance.options,
        }


def _pretty_json_dump(d):
    """Returns a human-readable JSON serialization of a value."""
    return json.dumps(d, sort_keys=True, indent=3)
