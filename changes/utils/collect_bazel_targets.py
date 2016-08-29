import sys
import json


targets = sys.stdin.read().splitlines()
out = {
    'cmd': '/usr/bin/bazel --output_user_root=%(bazel_root)s test --jobs=%(max_jobs)s {test_names}',
    'tests': targets,
}
json.dump(out, sys.stdout)
