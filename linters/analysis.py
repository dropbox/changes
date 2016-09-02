# This file is taken unchanged from the server repo at dropbox/python_linters/analysis.py
from __future__ import absolute_import

import ast

import re


class AnalysisVisitor(object):
    def __init__(self, linters, path):
        self.items = []
        self.path = path
        self.ancestors = []

        def path_filter(path, path_pattern, exclude_path_pattern):
            if (exclude_path_pattern is not None and
                    re.search(exclude_path_pattern, path)):
                return False  # Matched exclude pattern
            if (path_pattern is not None and
                    not re.search(path_pattern, path)):
                return False  # Did not match include pattern
            return True

        # Pre-filter the linters we will be running because we already have the path
        self.linters = [
            linter_func
            for linter_func in linters
            if path_filter(self.path, linter_func.path_pattern, linter_func.exclude_path_pattern)
        ]

    def visit(self, node):

        for linter in self.linters:
            if type(linter.node_type) is set:
                if linter.node_type and type(node) not in linter.node_type:
                    continue
            else:
                if linter.node_type and type(node) != linter.node_type:
                    continue

            res = linter.linter_func(node, self.ancestors)
            returned = []
            if type(res) is list:
                returned = res
            if type(res) is dict:
                returned = [res]
            for item in returned:
                item["lineno"] = node.lineno
                item["col_offset"] = node.col_offset
                item['linter_name'] = linter.linter_func.__name__
            self.items += returned
        self.ancestors.append(node)

        for field, value in ast.iter_fields(node):
            if isinstance(value, list):
                self.ancestors.append(value)
                for item in value:
                    if isinstance(item, ast.AST):
                        self.visit(item)
                self.ancestors.pop()
            elif isinstance(value, ast.AST):
                self.visit(value)
        self.ancestors.pop()

class Matcher(object):
    def __init__(self, pattern, extract_expr):

        self.pattern = []
        for p in pattern:
            tree = ast.parse(p).body[0]
            if extract_expr:
                tree = tree.value
            self.pattern.append(tree)

    def __call__(self, node):

        def is_placeholder(node, magic_strs):
            return (
                node in magic_strs or
                type(node) == ast.Name and is_placeholder(node.id, magic_strs) or
                type(node) == ast.Expr and is_placeholder(node.value, magic_strs) or
                type(node) == list and len(node) == 1 and is_placeholder(node[0], magic_strs) or
                type(node) == ast.alias and node.asname is None and is_placeholder(node.name, magic_strs)
            )


        def match_recurse(pattern_node, actual_node, collected):
            supertypes = [actual_node.__class__]
            while supertypes[-1] != object:
                supertypes.append(supertypes[-1].__base__)

            if is_placeholder(pattern_node, ["__" + t.__name__ for t in supertypes]):
                collected.append(actual_node)
                return True
            elif type(pattern_node) != type(actual_node):
                return False
            elif isinstance(pattern_node, ast.AST):
                return all(
                    match_recurse(left, right, collected)
                    for ((left_name, left), (right_name, right))
                    in zip(ast.iter_fields(pattern_node), ast.iter_fields(actual_node))
                )
            elif isinstance(pattern_node, list):
                if len(pattern_node) != len(actual_node):
                    return False
                else:
                    return all(
                        match_recurse(left, right, collected)
                        for (left, right) in zip(pattern_node, actual_node)
                    )
            else:
                if pattern_node == "__" and type(actual_node) is str:
                    collected.append(actual_node)
                    return True
                else:
                    return pattern_node == actual_node

        collected = []

        matched = False

        for tree in self.pattern:

            if match_recurse(tree, node, collected):
                matched = True
        if matched:
            return collected
        else:
            return None



def match_expr(*pattern):
    """
    Lets you match the ast.AST node of a python expression against a python
    "pattern" and extract values from it

    Performs the match against the AST, and thus ignores all formatting and
    whitespace. As long as the parsed trees match, it matches and returns
    not-None. Returns `None` if they do not match.

    You can use "__wildcards" to mark parts of the expression you do not care
    about, and these get returned in a list at the end of a match. Here are some
    example matches:

    - pattern "abs(__str)", code `abs(lol)` returns ["lol"]
    - pattern "__str(lol)", code `abs(lol)` returns ["abs"]

    You can control how broadly you want to match by changing the identifier at
    the end of the `__`. For example, changing `__str` to `__Name` makes it
    return the `ast.Name` node instead of the string inside it, giving you access
    to additional metadata e.g. line/column-offset if you want it

    - pattern "abs(__Name)", code `abs(lol)` returns [<_ast.Name at 0x103724350>"]

    You can also use `__list` to match multiple items when multiple items are
    present, e.g.

    - pattern "[a, b, c]", code `[a, b, c]` returns []

    But

    - pattern "[__list]", code `[a, b, c]` returns

    [[<_ast.Name at 0x10375aa10>,
      <_ast.Name at 0x10375aa90>,
      <_ast.Name at 0x10375aa50>]]

    Which is the list of ast.Name nodes inside that list literal.
    """
    return Matcher(pattern, True)


def match_stmt(*pattern):
    """Version of `match_expr` that allows you to match entire statements."""
    return Matcher(pattern, False)


def prettyprint_ast(node, show_attributes=False):
    """Better version of ast.dump that formats things nicely"""
    more = '    '
    def format(node, indent):
        if isinstance(node, ast.AST):
            body = []

            if node._fields:
                body += list(
                    '%s=%s' % (field, format(getattr(node, field), indent + more))
                    for field in node._fields
                )
            if show_attributes and node._attributes:
                body += list(
                    '%s=%s' % (a, format(getattr(node, a), indent + more))
                    for a in node._attributes
                )
            total_length = sum(len(stmt) for stmt in body) + len(body) * 2 + len(indent)
            if any("\n" in stmt for stmt in body) or total_length >= 80:
                inner = indent + more + (",\n" + indent + more).join(body) + "\n" + indent
                return node.__class__.__name__ + '(\n' + inner + ')'
            else:
                return node.__class__.__name__ + "(" + ", ".join(attr for attr in body) + ")"

        elif isinstance(node, list):
            if len(node) == 0:
                return '[]'
            else:
                return '[\n' + ',\n'.join(indent + more + format(x, indent + more) for x in node) + '\n' + indent + ']'
        return repr(node)
    if not isinstance(node, ast.AST):
        raise TypeError('expected AST, got %r' % node.__class__.__name__)
    return format(node, '')
