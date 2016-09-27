"""A collection of helper functions related to selective testing in Bazel
"""

import logging

from flask import current_app
from typing import Any, Dict, List, Tuple  # NOQA

from changes.constants import SelectiveTestingPolicy
from changes.models.project import Project, ProjectConfigError, ProjectOptionsHelper
from changes.utils.agg import aggregate_selective_testing_policy
from changes.vcs.base import InvalidDiffError

Project  # to silence lint error

logger = logging.getLogger(__name__)


def _no_whitelist_rule(project, project_config, sha, diff):
    # type: (Project, Dict[str, Any], str, str) -> Tuple[SelectiveTestingPolicy, str]
    whitelist = ProjectOptionsHelper.get_whitelisted_paths(project)
    if not whitelist:  # empty whitelist treated as None
        return SelectiveTestingPolicy.enabled, None
    return SelectiveTestingPolicy.disabled, "Project whitelist is not empty. Please check the Changes project admin page."


def _no_blacklist_rule(project, project_config, sha, diff):
    # type: (Project, Dict[str, Any], str, str) -> Tuple[SelectiveTestingPolicy, str]
    if not project_config['build.file-blacklist']:
        return SelectiveTestingPolicy.enabled, None
    return SelectiveTestingPolicy.disabled, "Project blacklist is not empty. Please check the config `build.file-blacklist`."


def _project_config_rule(project, project_config, sha, diff):
    # type: (Project, Dict[str, Any], str, str) -> Tuple[SelectiveTestingPolicy, str]
    if project_config['bazel.selective-testing-enabled']:
        return SelectiveTestingPolicy.enabled, None
    return SelectiveTestingPolicy.disabled, "Project config `bazel.selective-testing-enabled` is set to False."


def _global_config_rule(project, project_config, sha, diff):
    # type: (Project, Dict[str, Any], str, str) -> Tuple[SelectiveTestingPolicy, str]
    if current_app.config['SELECTIVE_TESTING_ENABLED']:
        return SelectiveTestingPolicy.enabled, None
    return SelectiveTestingPolicy.disabled, "Selective testing is globally disabled."


SELECTIVE_TESTING_RULES = [
    _global_config_rule,
    _project_config_rule,
    _no_whitelist_rule,
    _no_blacklist_rule,
]


def get_selective_testing_policy(project, sha, diff=None):
    """Given a project at a given revision and an optional diff,
    return the appropriate selective testing policy, along with
    a list of explanation for why the policy is chosen.
    """
    # type: (Project, str, str) -> Tuple[SelectiveTestingPolicy, List[str]]
    try:
        config = project.get_config(sha, diff)
    except ProjectConfigError:
        logger.exception('Project config for project %s is not in a valid format. Selective testing will not be done!', project.slug)
        return SelectiveTestingPolicy.disabled, ["Project config file not in valid format."]
    except InvalidDiffError:
        logger.exception('Unable to apply diff for project %s. Selective testing will not be done!', project.slug)
        return SelectiveTestingPolicy.disabled, ["Unable to apply diff."]
    except Exception:
        logger.exception('Exception occurred trying to parse project config for project %s.', project.slug)
        return SelectiveTestingPolicy.disabled, ["Unknown error while trying to read project config file."]
    results = [f(project=project, project_config=config, sha=sha, diff=diff) for f in SELECTIVE_TESTING_RULES]
    policy = aggregate_selective_testing_policy([p for (p, _) in results])
    reasons = [r for (_, r) in results if r is not None]
    return policy, reasons
