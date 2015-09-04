from __future__ import absolute_import, division

import os

from changes.constants import PROJECT_ROOT


def enforce_is_subdir(path, root=PROJECT_ROOT):
    """
    Ensure that a particular path is within a subdirectory of changes.
    Prevents directory traversal attacks
    """
    if not os.path.abspath(path).startswith(root):
        raise RuntimeError('this path is not safe!')
