from changes.api.serializer import Serializer, register
from changes.models.latest_green_build import LatestGreenBuild


@register(LatestGreenBuild)
class LatestGreenBuildSerializer(Serializer):
    def serialize(self, item, attrs):
        return {
            'branch': item.branch,
            'build': item.build,
        }
