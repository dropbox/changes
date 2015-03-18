"""Tools for tagging test outputs based on regexp based rules."""

import ast
import re


class ParseError(Exception):
    """Raised on syntax error in a rule."""


def load_rules(path):
    """Load rules from a file, a rule per line.

    Empty lines and lines containing only a comment starting with # are ignored.

    A rule is of form "tag:project:regexp" (whitespace around fields is ignored, project
    may be empty => applies to all projects). Regular expressions can be bare strings
    or quoted using Python string literal syntax (triple-quoted and raw string literals
    are supported, but unicode string literals are not valid).

    Return a list of (tag, regexp) tuples (both items are strings).
    """
    with open(path) as file:
        return parse_rules(file.read(), path)


def parse_rules(data, path='file'):
    rules = []
    for i, line in enumerate(data.splitlines()):
        try:
            rule = _parse_rule(line)
        except ParseError as exc:
            raise ParseError('%s, line %d: %s' % (path, i + 1, str(exc)))
        if rule:
            rules.append(rule)
    return rules


def _parse_rule(line):
    """Parse line of text that represents a rule.

    Return None if the line is empty or a comment. Otherwise, return tuple
    (tag, project, regular expression string).

    Raise ParseError on error.
    """
    line = line.strip()
    if not line or line.startswith('#'):
        return None
    try:
        tag, project, regexp = line.split(':', 2)
    except ValueError:
        raise ParseError("syntax error")
    regexp = _parse_regexp(regexp)
    return tag.strip(), project.strip(), regexp


def _parse_regexp(regexp):
    regexp = regexp.strip()
    # Parse quoted regular expressions as Python string literals.
    if regexp.endswith(('"', "'")):
        try:
            parsed = ast.literal_eval(regexp)
        except SyntaxError as exc:
            raise ParseError("invalid Python string literal")
        # We don't want unicode regexps for now.
        if not isinstance(parsed, str):
            raise ParseError("syntax error")
        regexp = parsed
    elif regexp.startswith(('"', "'")):
        raise ParseError("mismatched quotes")
    # Make sure that the regexp is valid.
    try:
        re.compile(regexp)
    except re.error as exc:
        raise ParseError(str(exc))
    return regexp


def categorize(project, rules, output):
    """Categorize test output based on rules.

    Args:
      project (str): name of the project
      rules (iterable of (str, str, str) tuples):
          each rule is a tuple (tag, project, regexp) that is matched against output
      output (str): output of a (partial) test run / build

    Returns:
      A tuple of sets with (matched_categories, applicable_categories), where
      applicable_categories are the names of rules that apply to the provided project.
      applicable_categories is a superset of matched_categories.
    """
    output = output.replace('\r\n', '\n')
    matched, applicable = set(), set()
    for tag, rule_project, regexp in rules:
        if not rule_project or rule_project == project:
            applicable.add(tag)
            if re.search(regexp, output, re.MULTILINE | re.DOTALL):
                matched.add(tag)
    return (matched, applicable)
