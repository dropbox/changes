from __future__ import absolute_import, print_function

from .manager import Manager
from .coverage import CoverageHandler
from .xunit import XunitHandler
from .manifest_json import ManifestJsonHandler


manager = Manager()
manager.register(CoverageHandler)
manager.register(ManifestJsonHandler)
manager.register(XunitHandler)
