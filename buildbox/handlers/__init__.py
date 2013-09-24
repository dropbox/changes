from .xunit import XunitHandler
from .coverage import CoverageHandler


ARTIFACT_HANDLERS = {
    'xunit.xml': XunitHandler,
    'coverage.xml': CoverageHandler,
}
