import os

from flask import current_app


BASH_BAZEL_SETUP = """#!/bin/bash -eux
# Clean up any existing apt sources
sudo rm -rf /etc/apt/sources.list.d
# Overwrite apt sources
echo "{apt_spec}" | sudo tee /etc/apt/sources.list

# apt-get update, and try again if it fails first time
sudo apt-get -y update || sudo apt-get -y update
sudo apt-get install -y --force-yes {bazel_apt_pkgs}

/usr/bin/bazel --nomaster_blazerc --blazerc=/dev/null --output_user_root={bazel_root} --batch version
""".strip()

# We run setup again because changes does not run setup before collecting tests, but we need bazel
# to collect tests. (also install python because it is needed for jsonification script)
# We also redirect stdout and stderr to /dev/null because changes uses the output of this
# script to collect tests, and so we don't want extraneous output.
COLLECT_BAZEL_TARGETS = """#!/bin/bash -eu
# Clean up any existing apt sources
sudo rm -rf /etc/apt/sources.list.d >/dev/null 2>&1
# Overwrite apt sources
(echo "{apt_spec}" | sudo tee /etc/apt/sources.list) >/dev/null 2>&1

# apt-get update, and try again if it fails first time
(sudo apt-get -y update || sudo apt-get -y update) >/dev/null 2>&1
sudo apt-get install -y --force-yes {bazel_apt_pkgs} python >/dev/null 2>&1

python -c "{script}" "{bazel_root}" "{bazel_targets}" "{bazel_exclude_tags}" "{max_jobs}" 2> /dev/null
""".strip()


SYNC_ENCAP_PKG = """
sudo /usr/bin/rsync -a --delete {encap_rsync_url}{pkg} {encap_dir}
""".strip()


def get_bazel_setup():
    return BASH_BAZEL_SETUP.format(
        apt_spec=current_app.config['APT_SPEC'],
        bazel_apt_pkgs=' '.join(current_app.config['BAZEL_APT_PKGS']),
        bazel_root=current_app.config['BAZEL_ROOT_PATH'],
    )


def collect_bazel_targets(bazel_targets, bazel_exclude_tags, max_jobs):
    """Construct a command to query the Bazel dependency graph to expand bazel project
    config into a set of individual test targets.

    Bazel project config currently supports the following attributes:
    - targets: List of Bazel target patterns (conforming to the spec given in
      https://www.bazel.io/docs/bazel-user-manual.html#target-patterns). These patterns
      are additive, meaning a union of all targets matching any of the patterns will be
      returned.
    - exclude-tags: List of target tags. Targets matching any of these tags are not returned.
      By default, this list is empty.
    """
    # type: (List[str], List[str], int) -> str
    package_dir = os.path.dirname(__file__)
    bazel_target_py = os.path.join(package_dir, "collect_bazel_targets.py")

    with open(bazel_target_py, 'r') as script:
        return COLLECT_BAZEL_TARGETS.format(
            apt_spec=current_app.config['APT_SPEC'],
            bazel_apt_pkgs=' '.join(current_app.config['BAZEL_APT_PKGS']),
            bazel_root=current_app.config['BAZEL_ROOT_PATH'],
            bazel_targets=','.join(bazel_targets),
            script=script.read().replace(r'"', r'\"').replace(r'$', r'\$').replace(r'`', r'\`'),
            bazel_exclude_tags=','.join(bazel_exclude_tags),
            max_jobs=max_jobs,
        )


def sync_encap_pkgs(project_config, encap_dir='/usr/local/encap/'):
    dependencies = project_config.get('bazel.dependencies', {})
    encap_pkgs = dependencies.get('encap', [])

    def sync_pkg(pkg):
        return SYNC_ENCAP_PKG.format(
            encap_rsync_url=current_app.config['ENCAP_RSYNC_URL'],
            pkg=pkg,
            encap_dir=encap_dir,
        )
    return '\n'.join(['sudo mkdir -p ' + encap_dir] + map(sync_pkg, encap_pkgs))
