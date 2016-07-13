import sys
import json


targets = sys.stdin.read().splitlines()
out = {
    'cmd': 'bazel test {test_names}',
    'tests': targets,
}
json.dump(out, sys.stdout)
