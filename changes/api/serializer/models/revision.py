from __future__ import absolute_import

from flask import current_app

from changes.api.serializer import Crumbler, register
from changes.config import db
from changes.models import ItemOption, Revision


@register(Revision)
class RevisionCrumbler(Crumbler):
    def get_extra_attrs_from_db(self, item_list):
        repo_ids = set(i.repository_id for i in item_list)

        callsigns = dict(db.session.query(
            ItemOption.item_id, ItemOption.value
        ).filter(
            ItemOption.item_id.in_(repo_ids)
        ))

        result = {}
        for item in item_list:
            result[item] = {
                'phabricator.callsign': callsigns.get(item.repository_id),
            }

        return result

    def crumble(self, instance, attrs):
        callsign = attrs['phabricator.callsign']
        if callsign and current_app.config['PHABRICATOR_LINK_HOST']:
            label = 'r{}{}'.format(callsign, instance.sha[:12])
            external = {
                'link': '{}/{}'.format(
                    current_app.config['PHABRICATOR_LINK_HOST'].rstrip('/'),
                    label),
                'label': label,
            }
        else:
            external = None

        return {
            'id': instance.sha,
            'repository': {
                'id': instance.repository_id,
            },
            'sha': instance.sha,
            'message': instance.message,
            'author': instance.author,
            'parents': instance.parents,
            'dateCreated': instance.date_created,
            'dateCommitted': instance.date_committed,
            'external': external,
        }
