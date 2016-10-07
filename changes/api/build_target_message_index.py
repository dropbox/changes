from changes.api.base import APIView, error
from changes.models.bazeltarget import BazelTarget
from changes.models.bazeltargetmessage import BazelTargetMessage


class BuildTargetMessageIndex(APIView):
    def get(self, build_id, target_id):
        target = BazelTarget.query.get(target_id)
        if not target:
            return error('target not found', http_code=404)
        queryset = BazelTargetMessage.query.filter(
            BazelTargetMessage.target_id == target.id,
        ).order_by(BazelTargetMessage.date_created.asc())

        return self.paginate(queryset)
