# This file is taken from the server repo (dropbox/python_linters/main.py) and
# changed to output in a format that arc understands (--arc-out option).
from __future__ import absolute_import
"Used to run the python AST linters on a set of files. Normally run through bin/lint"

import ast
import argparse
import json
import multiprocessing
import os
import random as insecure_random
import re
import textwrap

import sys

from linters.analysis import AnalysisVisitor, prettyprint_ast
from linters.linters import all_linters

server_root = os.path.dirname(__file__) + '/..'


def check_test_case(filename):
    print "Checking", filename
    with open(filename) as f:
        parsed = ast.parse(f.read(), filename)

    expected_stmt = parsed.body[-1]
    no_expected_msg = "Can't find `expected =` block at end of test file"
    assert type(expected_stmt) == ast.Assign, no_expected_msg
    assert len(expected_stmt.targets) == 1, no_expected_msg
    assert expected_stmt.targets[0].id == "expected", no_expected_msg

    expected = ast.literal_eval(expected_stmt.value)

    visitor = AnalysisVisitor(all_linters, filename)
    for stmt in parsed.body[:-1]:
        visitor.visit(stmt)
    assert visitor.items == expected, json.dumps({
        "filename": filename,
        "expected": expected,
        "actual": visitor.items
    }, indent=4)


def check_all():
    for (dirpath, dirname, filenames) in os.walk(os.path.dirname(__file__) + "/test/"):
        for filename in filenames:
            check_test_case(dirpath + "/" + filename)


def run(enforce_paths, linters, json_out, arc_out, run_all):
    output = []

    # Walk all folders in `enforce_paths`, but make sure we de-duplicate things
    # in case someone passes in the same file twice or both a folder and a single
    # file inside it.
    seen = set()
    items = []
    for enforce_path in enforce_paths:
        if not os.path.isdir(enforce_path):
            path = os.path.relpath(
                os.path.normpath(enforce_path),
                server_root
            )
            items.append(path)
            seen.add(path)
        else:
            for (dirpath, dirnames, filenames) in os.walk(enforce_path):
                for filename in filenames:
                    if filename.endswith(".py"):
                        path = os.path.relpath(
                            os.path.normpath(dirpath + "/" + filename),
                            server_root
                        )
                        if path not in seen:
                            seen.add(path)
                            items.append(path)
                dirnames[:] = [d for d in dirnames if not d.startswith(".")]

    if not json_out:
        count_msg = len(linters) if run_all else "enforced"
        print "Running", count_msg, "linters on", len(items), "files"

    pool = multiprocessing.Pool()
    results = pool.map(
        run_on_file,
        [(item, linters, run_all, json_out) for item in items]
    )
    for res in results:
        if res:
            item_output, item_lines = res

            output += item_output

    pool.close()
    if json_out:
        print json.dumps(output, indent=4)
    elif arc_out:
        print arc_output(output)
    else:
        print prettyprint_output(output)


def run_on_file(args):

    filepath, linters, run_all, json_out = args
    enforced_linters = [
        linter
        for linter in linters
        if linter.enforce_pattern is not None and re.match(linter.enforce_pattern, filepath) or run_all
    ]

    res = visit_path(enforced_linters, filepath)

    # Print a rough "progress" bar approx once every 177 files so people can
    # See the linter making progress when running on a large set of files
    if not json_out and insecure_random.random() > 0.99:
        sys.stdout.write(".")
        sys.stdout.flush()

    return res


def visit_path(linters, filepath):
    output = []

    visitor = AnalysisVisitor(linters, filepath)
    try:
        with open(filepath) as f:
            txt = f.read()
        parsed = ast.parse(txt, filepath)

        visitor.visit(parsed)

        for item in visitor.items:
            item["filepath"] = filepath
            output.append(item)

        return output, len(txt.split("\n"))

    except IOError:
        # This happens when you can't read a file because it's a
        # broken symlink
        pass


def prettyprint_output(lint_output):
    linters_to_warnings = {}
    for lint_warning in lint_output:
        if lint_warning['linter_name'] not in linters_to_warnings:
            linters_to_warnings[lint_warning['linter_name']] = []
        linters_to_warnings[lint_warning['linter_name']].append(lint_warning)

    output = []

    for linter_name, warnings in linters_to_warnings.items():
        output += [warnings[0]['linter_name']]
        output += ["=" * len(warnings[0]['linter_name'])]
        output += textwrap.wrap(warnings[0]['desc'])
        output += [""]
        for warning in warnings:
            output += [warning['filepath'] + ":" + str(warning['lineno'])]
        output += [""]

    return "\n".join(output)

def arc_output(lint_output):
    lines = []
    for lint_warning in lint_output:
        lines.append('{severity}:{line_number} {message}'.format(
            severity=lint_warning['severity'],
            line_number=lint_warning['lineno'],
            message=lint_warning['desc'],
        ))
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Runs our Python linters on the server codebase')
    parser.add_argument('TARGETS', nargs="*", help=
        "Run all lint rules on a file or folder"
    )
    parser.add_argument('--test', metavar="TEST_FILES", nargs="?", help=
        "Run the linter's internal unit tests in a single file or folder; "
        "used when writing a linter and writing tests to ensure the linter "
        "picks up the things you would expect."
    )
    parser.add_argument('--dump', metavar="TARGET", nargs="?", help=
        "dumps the file to a nicely-formatted AST "
        "for you to read. Useful when writing your linter to try and figure out "
        "how to match a particular piece of code via it's AST"
    )
    parser.add_argument('--all', dest="all", action='store_const', const=True, help=
        "Run all the linters, not just the ones that are breaking the build"
    )
    parser.add_argument('--linter', nargs="?", help=
        "Specify a single linter to run, by name. e.g. `--linter accessibility` or "
        "`--linter ip_logging`, rather than the all linters that are breaking the build."
    )
    parser.add_argument('--json-out', dest="json_out", action='store_const', const=True, help=
        "Dump output to JSON instead of human-readable text"
    )
    parser.add_argument('--arc-out', dest='arc_out', action='store_const', const=True, help=
        "Dump output in an arc compatible format, assuming the regex pattern arc wants"
        " is /^(?P<severity>advice|warning|error):(?P<line>\\d+) (?P<message>.*)$/m."
        "--json-out takes precedence over this.")
    args = parser.parse_args()

    if args.linter:
        linters = [
            linter for linter in all_linters
            if linter.linter_func.__name__ == args.linter + "_linter"
        ]
        run_all = True
    else:
        linters = all_linters
        run_all = args.all

    if args.test == "all":
        check_all()
    elif args.test:
        check_test_case(args.test)
    elif args.dump:
        with open(args.dump) as f:
            parsed = ast.parse(f.read(), args.dump)
            print prettyprint_ast(parsed)

    else:
        run(
            args.TARGETS or [server_root],
            linters,
            args.json_out,
            args.arc_out,
            run_all=run_all
        )

if __name__ == "__main__":
    main()
