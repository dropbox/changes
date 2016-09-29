from flask import current_app

# Assume that apt sources have been set up correctly up front, and `apt-get update` run already.
BASH_BAZEL_SETUP = """#!/bin/bash -eux
sudo apt-get install -y --force-yes {bazel_apt_pkgs}
""".strip()

# We run setup again because changes does not run setup before collecting tests, but we need bazel
# to collect tests. (also install python because it is needed for jsonification script)
# We also redirect stdout and stderr to /dev/null because changes uses the output of this
# script to collect tests, and so we don't want extraneous output.
COLLECT_BAZEL_TARGETS = """#!/bin/bash -eu
sudo apt-get install -y --force-yes {bazel_apt_pkgs} python >/dev/null 2>&1

"{collect_targets_executable}" --output-user-root="{bazel_root}" {bazel_targets} {bazel_exclude_tags} {bazel_test_flags} --jobs="{max_jobs}" 2> /dev/null
""".strip()


SYNC_ENCAP_PKG = """
sudo /usr/bin/rsync -a --delete {encap_rsync_url}{pkg} {encap_dir}
""".strip()


def get_bazel_setup():
    return BASH_BAZEL_SETUP.format(
        bazel_apt_pkgs=' '.join(current_app.config['BAZEL_APT_PKGS']),
        bazel_root=current_app.config['BAZEL_ROOT_PATH'],
    )


def collect_bazel_targets(collect_targets_executable, bazel_targets, bazel_exclude_tags, bazel_test_flags, max_jobs):
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
    # type: (str, List[str], List[str], int, changes.vcs.base.Vcs) -> str
    return COLLECT_BAZEL_TARGETS.format(
        bazel_apt_pkgs=' '.join(current_app.config['BAZEL_APT_PKGS']),
        bazel_root=current_app.config['BAZEL_ROOT_PATH'],
        bazel_targets=' '.join(['--target-patterns={}'.format(t) for t in bazel_targets]),
        collect_targets_executable=collect_targets_executable,
        bazel_exclude_tags=' '.join(['--exclude-tags={}'.format(t) for t in bazel_exclude_tags]),
        bazel_test_flags=' '.join(['--test-flags={}'.format(tf) for tf in bazel_test_flags]),
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
