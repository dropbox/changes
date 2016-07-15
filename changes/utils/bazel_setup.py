import os

from flask import current_app


BASH_BAZEL_SETUP = """#!/bin/bash -eux
echo "%(apt_spec)s" | sudo tee /etc/apt/sources.list.d/bazel-changes-autogen.list
sudo apt-get update || true
sudo apt-get install -y --force-yes bazel drte-v1 gcc unzip zip
""".strip()

# We run setup again because changes does not run setup before collecting tests, but we need bazel
# to collect tests. (also install python because it is needed for jsonification script)
# We also redirect stdout and stderr to /dev/null because changes uses the output of this
# script to collect tests, and so we don't want extraneous output.
COLLECT_BAZEL_TARGETS = """#!/bin/bash -eu
echo "%(apt_spec)s" | sudo tee /etc/apt/sources.list.d/bazel-changes-autogen.list > /dev/null 2>&1
(sudo apt-get update || true) > /dev/null 2>&1
sudo apt-get install -y --force-yes bazel drte-v1 gcc unzip zip python > /dev/null 2>&1
(bazel query 'tests(%(bazel_targets)s)' | python -c "%(jsonify_script)s") 2> /dev/null
""".strip()


SYNC_ENCAP_PKG = """
sudo rsync -a --delete %(encap_rsync_url)s%(pkg)s %(encap_dir)s
""".strip()


def get_bazel_setup():
    return BASH_BAZEL_SETUP % dict(
        apt_spec=current_app.config['APT_SPEC']
    )


def collect_bazel_targets(bazel_targets):
    package_dir = os.path.dirname(__file__)
    bazel_target_py = os.path.join(package_dir, "collect_bazel_targets.py")
    with open(bazel_target_py, 'r') as jsonify_script:
        return COLLECT_BAZEL_TARGETS % dict(
            apt_spec=current_app.config['APT_SPEC'],
            bazel_targets=' + '.join(bazel_targets),
            jsonify_script=jsonify_script.read()
        )


def sync_encap_pkgs(project_config, encap_dir='/usr/local/encap/'):
    dependencies = project_config.get('bazel.dependencies', {})
    encap_pkgs = dependencies.get('encap', [])

    def sync_pkg(pkg):
        return SYNC_ENCAP_PKG % dict(
            encap_rsync_url=current_app.config['ENCAP_RSYNC_URL'],
            pkg=pkg,
            encap_dir=encap_dir,
        )
    return '\n'.join(['sudo mkdir -p ' + encap_dir] + map(sync_pkg, encap_pkgs))
