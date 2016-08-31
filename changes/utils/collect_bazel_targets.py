import json
import subprocess
import sys


BAZEL_PATH = '/usr/bin/bazel'

BAZEL_FLAGS = ['--nomaster_blazerc', '--blazerc=/dev/null']


def main(argv):
    """Collect bazel targets. This runs a query against Bazel to determine
    the list of test targets to run. It also queries Bazel for the artifact
    search path, which is passed back to Changes.

    `argv` contains the command line arguments. There must be exactly 4, in
    this order:
    - bazel root output path
    - comma-separated list of bazel targets
    - comma-separated list of bazel exclude tags
    - the maximum number of jobs to run per command
    """
    bazel_root = argv[0]
    bazel_targets = [x for x in argv[1].split(',') if x != '']
    bazel_exclude_tags = [x for x in argv[2].split(',') if x != '']
    max_jobs = argv[3]

    # Please use https://www.bazel.io/docs/query.html as a reference for Bazel query syntax
    #
    # To exclude targets matching a tag, we construct a query as follows:
    #   let t = test(bazel_targets)                     ## Collect list of test targets in $t
    #   return $t except attr("tags", $expression, $t)  ## Return all targets in t except those where "tags" matches an expression
    #
    # Multiple exclusions a performed by adding further "except" clauses
    #   return $t except attr(1) expect attr(2) except attr(3) ...
    #
    # Examples of "tags" attribute:
    #   []                                              ## No tags
    #   [flaky]                                         ## Single tag named flaky
    #   [flaky, manual]                                 ## Two tags named flaky and manual
    #
    # Tags are delimited on the left by an opening bracket or space, and on the right by a comma or closing bracket.
    #
    # Hence, $expression =>
    #   (\[| )                                          ## Starts with an opening bracket or space
    #   tag_name                                        ## Match actual tag name
    #   (\]|,)                                          ## Ends with a closing bracket or comma
    exclusion_subquery = ' '.join(["""except (attr("tags", "(\[| ){}(\]|,)", $t))""".format(
        tag) for tag in bazel_exclude_tags])

    targets = subprocess.check_output(
        [BAZEL_PATH] + BAZEL_FLAGS + [
            '--output_user_root={}'.format(bazel_root),
            '--batch',
            'query',
            'let t = tests({targets}) in ($t {exclusion_subquery})'.format(
                targets=' + '.join(bazel_targets),
                exclusion_subquery=exclusion_subquery
            ),
        ]).strip().splitlines()

    artifact_search_path = subprocess.check_output(
        [BAZEL_PATH] + BAZEL_FLAGS + [
            '--output_user_root={}'.format(bazel_root),
            '--batch',
            'info',
            'bazel-testlogs',
        ]).strip()
    out = {
        'cmd': '/usr/bin/bazel --output_user_root={bazel_root} test --jobs={max_jobs} {{test_names}}'.format(bazel_root=bazel_root, max_jobs=max_jobs),
        'tests': targets,
        'artifact_search_path': artifact_search_path,
        'artifacts': ['*.xml'],
    }
    json.dump(out, sys.stdout)
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
