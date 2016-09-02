from __future__ import absolute_import
"""
Linters that operate on the Python AST, receiving an AST node and returning
{"desc", "severity"} tuples if it doesn't like something. The
`@register_linter` decorator is used to register each linter to be run, and
allows configuration of the AST node types and file paths on which it will be
run.

Check out the Python documentation on ASTs https://docs.python.org/2/library/ast.html
if you want to see what kind of data structure they are.

NOTE: This file structure is copied from the server repo, and the linters in here
can be copied directly into `dropbox/python_linters/linters.py` when we move
into the server repo.
"""

import ast

from collections import namedtuple

from linters.analysis import match_expr

all_linters = []

Linter = namedtuple(
    "Linter",
    ["node_type", "path_pattern", "exclude_path_pattern",
        "linter_func", "enforce_pattern"]
)


def register_linter(node_type=None, path_pattern=None, enforce_pattern=None, exclude_path_pattern=None):
    """
    Registers a linter so it gets used when you call `./dropbox/python_linters/lint`

    - node_type: type or set of types of AST nodes to run on
    - path_pattern: regexp that file paths must match for this linter to be run
    - exclude_path_pattern: regexp that file paths must NOT match for this
      linter to be run

    Both pattern arguments are optional; if not provided no path filter will be
    applied.

    Note that paths are filesystem-absolute so patterns should probably not
    start with ^.

    Each linter function takes the node (as well as a list of `ancestors` of that
    node) and can return a dict of {"desc": ..., "severity": ...} that indicates
    there's a lint violation. Other details like file-name, line-number, etc.
    are filled in automatically.
    """

    def foo(linter):
        all_linters.append(Linter(
            node_type,
            path_pattern,
            exclude_path_pattern,
            linter,
            enforce_pattern
        ))
        return linter

    return foo


# Everything from this line onward should be copied into dropbox/python_linters/linters.py
# when we move to the server repo.


# list of tables that should not be modified
FORBIDDEN_TABLES = ['test']

FORBIDDEN_TABLE_MATCHERS = [((match_expr("'{}'".format(t))), t)
                            for t in FORBIDDEN_TABLES]

# list of operations that should not be allowed on the forbidden tables.
# the first value is the function name, and the second is the argument position
# in which the table name appears, with 0 being the first argument.
FORBIDDEN_OP = [
    ('add_column', 0),
    ('alter_column', 0),
    ('batch_alter_table', 0),
    ('create_check_constraint', 1),
    ('create_foreign_key', 1),
    ('create_index', 1),
    ('create_primary_key', 1),
    ('create_unique_constraint', 1),
    ('drop_column', 0),
    ('drop_constraint', 1),
    ('drop_index', 1),
]

FORBIDDEN_OP_MATCHERS = [(match_expr('op.{}'.format(f[0])), f[1])
                         for f in FORBIDDEN_OP]


@register_linter(ast.Call, enforce_pattern='migrations/versions')
def prevent_table_modification_linter(node, ancestors):
    for op_matcher, pos in FORBIDDEN_OP_MATCHERS:
        if len(node.args) > pos and op_matcher(node.func) is not None:
            for table_matcher, table_name in FORBIDDEN_TABLE_MATCHERS:
                if table_matcher(node.args[pos]) is not None:
                    return {
                        "desc":
                            "Please don't modify the {} table. Doing so has "
                            "caused unavailability in production in the past.".format(
                                table_name),
                        "severity": "warning",
                    }
