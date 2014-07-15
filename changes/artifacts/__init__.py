from __future__ import absolute_import, print_function

from .manager import Manager
from .coverage import CoverageHandler
from .xunit import XunitHandler


manager = Manager()
manager.register(CoverageHandler, ['coverage.xml'])
manager.register(XunitHandler, ['xunit.xml', 'junit.xml'])
