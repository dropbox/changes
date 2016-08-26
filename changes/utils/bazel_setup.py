import os

from flask import current_app


BASH_BAZEL_SETUP = """#!/bin/bash -eux
# Clean up any existing apt sources
sudo rm -rf /etc/apt/sources.list.d
# Overwrite apt sources
echo "%(apt_spec)s" | sudo tee /etc/apt/sources.list

# apt-get update, and try again if it fails first time
sudo apt-get -y update || sudo apt-get -y update
sudo apt-get install -y --force-yes %(bazel_apt_pkgs)s

/usr/bin/bazel --nomaster_blazerc --blazerc=/dev/null --batch version
""".strip()

# We run setup again because changes does not run setup before collecting tests, but we need bazel
# to collect tests. (also install python because it is needed for jsonification script)
# We also redirect stdout and stderr to /dev/null because changes uses the output of this
# script to collect tests, and so we don't want extraneous output.
COLLECT_BAZEL_TARGETS = """#!/bin/bash -eu
# Clean up any existing apt sources
sudo rm -rf /etc/apt/sources.list.d >/dev/null 2>&1
# Overwrite apt sources
(echo "%(apt_spec)s" | sudo tee /etc/apt/sources.list) >/dev/null 2>&1

# apt-get update, and try again if it fails first time
(sudo apt-get -y update || sudo apt-get -y update) >/dev/null 2>&1
sudo apt-get install -y --force-yes %(bazel_apt_pkgs)s python >/dev/null 2>&1

(/usr/bin/bazel --nomaster_blazerc --blazerc=/dev/null --batch query \
    'let t = tests(%(bazel_targets)s) in ($t %(exclusion_subquery)s)' | \
    python -c "%(jsonify_script)s") 2> /dev/null
""".strip()


SYNC_ENCAP_PKG = """
sudo /usr/bin/rsync -a --delete %(encap_rsync_url)s%(pkg)s %(encap_dir)s
""".strip()


def get_bazel_setup():
    return BASH_BAZEL_SETUP % dict(
        apt_spec=current_app.config['APT_SPEC'],
        bazel_apt_pkgs=' '.join(current_app.config['BAZEL_APT_PKGS']),
    )


def collect_bazel_targets(bazel_targets, bazel_exclude_tags):
    """Construct a command to query the Bazel dependency graph to expand bazel project
    config into a set of individual test targets.

    Bazel project config currently supports the following attributes:
    - targets: List of Bazel target patterns (conforming to the spec given in
      https://www.bazel.io/docs/bazel-user-manual.html#target-patterns). These patterns
      are additive, meaning a union of all targets matching any of the patterns will be
      returned.
    - exclude-tags: List of target tags. Targets matching any of these tags are not returned.
      By default, this list is empty.  # TODO(anupc): Should we remove `manual` test targets?
    """
    package_dir = os.path.dirname(__file__)
    bazel_target_py = os.path.join(package_dir, "collect_bazel_targets.py")

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
    exclusion_subquery = ' '.join(["""except (attr("tags", "(\[| )%s(\]|,)", $t))""" % (tag) for tag in bazel_exclude_tags])

    with open(bazel_target_py, 'r') as jsonify_script:
        return COLLECT_BAZEL_TARGETS % dict(
            apt_spec=current_app.config['APT_SPEC'],
            bazel_apt_pkgs=' '.join(current_app.config['BAZEL_APT_PKGS']),
            bazel_targets=' + '.join(bazel_targets),
            jsonify_script=jsonify_script.read(),
            exclusion_subquery=exclusion_subquery,
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
