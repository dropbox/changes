from changes.api.serializer import Crumbler, register
from changes.models.latest_green_build import LatestGreenBuild


@register(LatestGreenBuild)
class LatestGreenBuildCrumbler(Crumbler):
    def crumble(self, item, attrs):
        return {
            'branch': item.branch,
            'build': item.build,
        }
