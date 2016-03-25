#!/usr/bin/env python

"""Run a script and generate a junit.xml file.

If the script has exit status 0, the junit.xml will have one
successful test.

Otherwise, the junit.xml will have a failed or error test (specific
rules are in the code below).

Stdout and stderr are copied to the program's stdout and stderr.
They may also be included in the XML for fail/error tests.
"""

from __future__ import print_function

from xml.sax.saxutils import escape
import subprocess
import sys
import time


PASS_TEMPLATE = """<?xml version="1.0" encoding="utf-8"?>
<testsuite errors="0" failures="0" name="mypy" skips="0" tests="1" time="{time}">
  <testcase classname="mypy" file="mypy" line="1" name="mypy" time="{time}">
  </testcase>
</testsuite>
"""

FAIL_TEMPLATE = """<?xml version="1.0" encoding="utf-8"?>
<testsuite errors="0" failures="1" name="mypy" skips="0" tests="1" time="{time}">
  <testcase classname="mypy" file="mypy" line="1" name="mypy" time="{time}">
    <failure message="mypy produced messages">{text}</failure>
  </testcase>
</testsuite>
"""

ERROR_TEMPLATE = """<?xml version="1.0" encoding="utf-8"?>
<testsuite errors="1" failures="0" name="mypy" skips="0" tests="1" time="{time}">
  <testcase classname="mypy" file="mypy" line="1" name="mypy" time="{time}">
    <error message="mypy produced errors">{text}</error>
  </testcase>
</testsuite>
"""


def main():
    # TODO: parse flags args
    cmd = sys.argv[1:]
    if not cmd:
        sys.stderr.write("Usage: run_mypy mypy <mypy-flags> <mypy-args>\n")
        return 2
    junit_file = 'mypy.junit.xml'

    t0 = time.time()
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    outb, errb = p.communicate()
    code = p.returncode
    t1 = time.time()
    dt = '%.3f' % (t1 - t0)

    out = outb.decode('utf-8')
    err = errb.decode('utf-8')

    if out:
        if not out.endswith("\n"):
            out += "\n"
        sys.stdout.write(out)
    if err:
        if not err.endswith("\n"):
            err += "\n"
        sys.stderr.write(err)

    if code == 0:
        print("Pass")
        xml = PASS_TEMPLATE.format(time=dt)
    # TODO(guido): Remove the "mypy:" check once mypy writes to stderr.
    elif code == 1 and not err and out and not out.startswith("mypy:"):
        print("Fail")
        xml = FAIL_TEMPLATE.format(text=escape(out), time=dt)
    else:
        print("Error")
        texts = []
        # TODO(guido): Use <system-out> and <system-error> once Changes supports them.
        if out:
            texts.append("=== stdout ===\n")
            texts.append(out)
        if err:
            texts.append("=== stderr ===\n")
            texts.append(err)
        text = "".join(texts)
        xml = ERROR_TEMPLATE.format(text=escape(text), time=dt)

    with open(junit_file, 'w') as f:
        f.write(xml)

    return code


if __name__ == '__main__':
    sys.exit(main())
