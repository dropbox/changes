from __future__ import absolute_import

from changes.testutils.fixtures import SAMPLE_DIFF_BYTES as COMPLEX_DIFF
from changes.testutils import TestCase
from changes.utils.diff_parser import DiffParser


SIMPLE_DIFF = """
diff --git a/changes/utils/diff_parser.py b/changes/utils/diff_parser.py
index c2a8485..0768aaa 100644
--- a/changes/utils/diff_parser.py
+++ b/changes/utils/diff_parser.py
@@ -71,6 +71,7 @@ class DiffParser(object):
                 continue
""" + ' ' + """
             chunks = []
+            chunk_markers = []
             old, new = self._extract_rev(line, lineiter.next())
             files.append({
                 'old_filename': old[0] if old[0] != '/dev/null' else None,
"""


class DiffParserTest(TestCase):

    def test_parse_simple_diff(self):
        parser = DiffParser(SIMPLE_DIFF)
        files = parser.parse()
        assert files == [
            {
                'old_filename': 'a/changes/utils/diff_parser.py',
                'new_filename': 'b/changes/utils/diff_parser.py',
                'chunk_markers': ['@@ -71,6 +71,7 @@ class DiffParser(object):'],
                'chunks': [[
                    {
                        'action': 'unmod',
                        'line': '                continue',
                        'new_lineno': 71,
                        'old_lineno': 71,
                        'ends_with_newline': True,
                    },
                    {
                        'action': 'unmod',
                        'line': '',
                        'new_lineno': 72,
                        'old_lineno': 72,
                        'ends_with_newline': True,
                    },
                    {
                        'action': 'unmod',
                        'line': '            chunks = []',
                        'new_lineno': 73,
                        'old_lineno': 73,
                        'ends_with_newline': True,
                    },
                    {
                        'action': 'add',
                        'line': '            chunk_markers = []',
                        'new_lineno': 74,
                        'old_lineno': u'',
                        'ends_with_newline': True,
                    },
                    {
                        'action': 'unmod',
                        'line': '            old, new = self._extract_rev(line, lineiter.next())',
                        'new_lineno': 75,
                        'old_lineno': 74,
                        'ends_with_newline': True,
                    },
                    {
                        'action': 'unmod',
                        'line': '            files.append({',
                        'new_lineno': 76,
                        'old_lineno': 75,
                        'ends_with_newline': True,
                    },
                    {
                        'action': 'unmod',
                        'line': "                'old_filename': old[0] if old[0] != '/dev/null' else None,",
                        'new_lineno': 77,
                        'old_lineno': 76,
                        'ends_with_newline': True,
                    }
                ]],
            }
        ]

    def test_parse_complex_diff(self):
        parser = DiffParser(COMPLEX_DIFF)
        files = parser.parse()
        assert len(files) == 3

    def test_get_changed_files_simple_diff(self):
        parser = DiffParser(SIMPLE_DIFF)
        files = parser.get_changed_files()
        assert files == set([
            'changes/utils/diff_parser.py',
        ])
        lines_by_file = parser.get_lines_by_file()
        assert lines_by_file == {'changes/utils/diff_parser.py': {74}}

    def test_get_changed_files_complex_diff(self):
        parser = DiffParser(COMPLEX_DIFF)
        files = parser.get_changed_files()
        assert files == set([
            'ci/run_with_retries.py',
            'ci/server-collect',
            'ci/not-real',
        ])
        lines_by_file = parser.get_lines_by_file()
        assert set(lines_by_file) == files
        assert lines_by_file['ci/not-real'] == {1}
        assert lines_by_file['ci/server-collect'] == {24, 31, 39, 46}
        assert lines_by_file['ci/run_with_retries.py'] == {2, 45} | set(range(53, 63)) | set(range(185, 192))

    def test_reconstruct_file_diff_simple_diff(self):
        parser = DiffParser(SIMPLE_DIFF)
        files = parser.parse()
        assert len(files) == 1
        diff = parser.reconstruct_file_diff(files[0])
        correct = """
--- a/changes/utils/diff_parser.py
+++ b/changes/utils/diff_parser.py
@@ -71,6 +71,7 @@ class DiffParser(object):
                 continue
""" + ' ' + """
             chunks = []
+            chunk_markers = []
             old, new = self._extract_rev(line, lineiter.next())
             files.append({
                 'old_filename': old[0] if old[0] != '/dev/null' else None,
"""
        assert diff == correct

    def test_reconstruct_file_diff_complex_diff(self):
        parser = DiffParser(COMPLEX_DIFF)
        files = parser.parse()
        diffs = set(parser.reconstruct_file_diff(x) for x in files)
        assert len(diffs) == 3
        correct = set([
            """
--- a/ci/run_with_retries.py
+++ b/ci/run_with_retries.py
@@ -1,4 +1,5 @@
 #!/usr/bin/env python
+import argparse
 import os
 import sys
 import subprocess
@@ -41,7 +42,7 @@
     return [testcase for testcase in root if testcase_status(testcase) in ('failure', 'error')]
""" + ' ' + """
""" + ' ' + """
-def run(files):
+def run(files, cwd):
     cmd = COVERAGE_COMMAND_LINE % PYTEST_COMMAND_LINE
     cmd = "%s %s" % (cmd % FINAL_JUNIT_XML_FILE, files)
     write_out("Running command: %s" % cmd)
@@ -49,6 +50,16 @@
     write_out("Generating coverage.xml")
     run_streaming_out(COVERAGE_XML_COMMAND_LINE)
""" + ' ' + """
+    new_file_text = ""
+    if os.path.isfile('%s/coverage.xml' % os.getcwd()):
+        write_out("Replacing all paths in coverage.xml with repo paths. \xe2\x98\x83")
+        with open('%s/coverage.xml' % os.getcwd(), 'r') as f:
+            file_text = f.read()
+            new_file_text = file_text.replace("filename='", "filename='%s" % cwd)
+
+        with open('%s/coverage.xml' % os.getcwd(), 'w') as f:
+            f.write(new_file_text)
+
     if junit_xml is None:
         # rerun original command, hence rerunning all tests.
         # this may be caused by a timeout.
@@ -171,5 +182,10 @@
     if os.path.isfile(test_file):
         subprocess.Popen("rm %s" % test_file)
""" + ' ' + """
-    files_args = ' '.join(sys.argv[1:])
-    run(files_args)
+    parser = argparse.ArgumentParser(description='Run the tests with retries')
+    parser.add_argument('filenames', metavar='filename', nargs='*', help="Files to run on")
+    parser.add_argument('--cwd', dest='cwd', help="path inside the repo to the cwd")
+
+    args = parser.parse_args()
+    files_args = ' '.join(args.filenames)
+    run(files_args, args.cwd)
""", """
--- a/ci/server-collect
+++ b/ci/server-collect
@@ -21,14 +21,14 @@
         'name': 'blockserver',
         'cwd': 'blockserver',
         'path': 'blockserver',
-        'exec': pytest_command_line,
+        'exec': pytest_command_line + ' --cwd blockserver/',
         'xunit': 'tests.xml',
     },
     'metaserver': {
         'name': 'metaserver',
         'cwd': 'metaserver',
         'path': 'metaserver',
-        'exec': pytest_command_line,
+        'exec': pytest_command_line + ' --cwd metaserver/',
         'xunit': 'tests.xml',
     },
     'dropbox': {
@@ -36,14 +36,14 @@
         'cwd': 'dropbox_tests',
         'path': 'dropbox/tests',
         'keep_path': 1,
-        'exec': pytest_command_line,
+        'exec': pytest_command_line + ' --cwd dropbox/',
         'xunit': 'tests.xml',
     },
     'shortserver': {
         'name': 'shortserver',
         'cwd': 'shortserver',
         'path': 'shortserver',
-        'exec': pytest_command_line,
+        'exec': pytest_command_line + ' --cwd shortserver/',
         'xunit': 'tests.xml',
     },
 }
""", """
--- a/ci/not-real
+++ b/ci/not-real
@@ -1 +1 @@
-Single Line
+Single Line!
"""
        ])
        assert correct == diffs

    def test_no_newline_source(self):
        patch = """diff --git a/test b/test
index d800886..190a180 100644
--- a/test
+++ b/test
@@ -1 +1 @@
-123
\ No newline at end of file
+123
"""
        parser = DiffParser(patch)
        (file_dict,) = parser.parse()
        diff = parser.reconstruct_file_diff(file_dict)
        assert diff == """
--- a/test
+++ b/test
@@ -1 +1 @@
-123
\ No newline at end of file
+123
"""

    def test_no_newline_target(self):
        patch = """diff --git a/test b/test
index 190a180..d800886 100644
--- a/test
+++ b/test
@@ -1 +1 @@
-123
+123
\ No newline at end of file
"""
        parser = DiffParser(patch)
        (file_dict,) = parser.parse()
        diff = parser.reconstruct_file_diff(file_dict)
        assert diff == """
--- a/test
+++ b/test
@@ -1 +1 @@
-123
+123
\ No newline at end of file
"""

    def test_no_newline_both(self):
        patch = """diff --git a/test b/test
index d800886..bed2d6a 100644
--- a/test
+++ b/test
@@ -1 +1 @@
-123
\ No newline at end of file
+123n
\ No newline at end of file
"""
        parser = DiffParser(patch)
        (file_dict,) = parser.parse()
        diff = parser.reconstruct_file_diff(file_dict)
        assert diff == """
--- a/test
+++ b/test
@@ -1 +1 @@
-123
\ No newline at end of file
+123n
\ No newline at end of file
"""

    def test_no_newline_empty_source(self):
        patch = """diff --git a/test b/test
index e69de29..d800886 100644
--- a/test
+++ b/test
@@ -0,0 +1 @@
+123
\ No newline at end of file
"""
        parser = DiffParser(patch)
        (file_dict,) = parser.parse()
        diff = parser.reconstruct_file_diff(file_dict)
        assert diff == """
--- a/test
+++ b/test
@@ -0,0 +1 @@
+123
\ No newline at end of file
"""

    def test_no_newline_empty_target(self):
        patch = """diff --git a/test b/test
index d800886..e69de29 100644
--- a/test
+++ b/test
@@ -1 +0,0 @@
-123
\ No newline at end of file
"""
        parser = DiffParser(patch)
        (file_dict,) = parser.parse()
        diff = parser.reconstruct_file_diff(file_dict)
        assert diff == """
--- a/test
+++ b/test
@@ -1 +0,0 @@
-123
\ No newline at end of file
"""

    def test_dev_null_source(self):
        patch = """diff --git a/whitelist/blacklist/a.txt b/whitelist/blacklist/a.txt
new file mode 100644
index 0000000..038d718
--- /dev/null
+++ b/whitelist/blacklist/a.txt
@@ -0,0 +1 @@
+testing
"""
        parser = DiffParser(patch)
        (file_dict,) = parser.parse()
        diff = parser.reconstruct_file_diff(file_dict)
        assert diff == """
--- /dev/null
+++ b/whitelist/blacklist/a.txt
@@ -0,0 +1 @@
+testing
"""
        assert file_dict['old_filename'] is None
        assert parser.get_changed_files() == set(['whitelist/blacklist/a.txt'])
        assert parser.get_lines_by_file() == {'whitelist/blacklist/a.txt': {1}}

    def test_dev_null_target(self):
        patch = """diff --git a/whitelist/blacklist/b.txt b/whitelist/blacklist/b.txt
deleted file mode 100644
index 038d718..0000000
--- a/whitelist/blacklist/b.txt
+++ /dev/null
@@ -1 +0,0 @@
-testing
"""
        parser = DiffParser(patch)
        (file_dict,) = parser.parse()
        diff = parser.reconstruct_file_diff(file_dict)
        assert diff == """
--- a/whitelist/blacklist/b.txt
+++ /dev/null
@@ -1 +0,0 @@
-testing
"""
        assert file_dict['new_filename'] is None
        assert parser.get_changed_files() == set(['whitelist/blacklist/b.txt'])
        assert parser.get_lines_by_file() == {}

    def test_remove_empty_file(self):
        patch = """diff --git a/diff-from/__init__.py b/diff-from/__init__.py
deleted file mode 100644
index e69de29..0000000
"""
        parser = DiffParser(patch)
        (file_dict,) = parser.parse()
        diff = parser.reconstruct_file_diff(file_dict)
        assert diff == ""
        assert file_dict['new_filename'] is None
        assert parser.get_changed_files() == set(['diff-from/__init__.py'])
        assert parser.get_lines_by_file() == {}

    def test_remove_multiple_empty_files(self):
        patch = """diff --git a/diff-from/__init__.py b/diff-from/__init__.py
deleted file mode 100644
index e69de29..0000000
diff --git a/diff-from/other.py b/diff-from/other.py
deleted file mode 100644
index e69de29..0000000
"""
        parser = DiffParser(patch)
        (first_dict, second_dict,) = parser.parse()
        assert first_dict['new_filename'] is None
        assert first_dict['old_filename'] == 'a/diff-from/__init__.py'
        assert second_dict['new_filename'] is None
        assert second_dict['old_filename'] == 'a/diff-from/other.py'
        assert parser.get_changed_files() == set(['diff-from/__init__.py', 'diff-from/other.py'])
        assert parser.get_lines_by_file() == {}

    def test_add_empty_file(self):
        patch = """diff --git a/diff-from/__init__.py b/diff-from/__init__.py
new file mode 100644
index 0000000..e69de29
"""
        parser = DiffParser(patch)
        (file_dict,) = parser.parse()
        diff = parser.reconstruct_file_diff(file_dict)
        assert diff == ""
        assert file_dict['old_filename'] is None
        assert parser.get_changed_files() == set(['diff-from/__init__.py'])
        assert parser.get_lines_by_file() == {}

    def test_add_multiple_empty_files(self):
        patch = """diff --git a/diff-from/__init__.py b/diff-from/__init__.py
new file mode 100644
index 0000000..e69de29
diff --git a/diff-from/other.py b/diff-from/other.py
new file mode 100644
index 0000000..e69de29
"""
        parser = DiffParser(patch)
        (first_dict, second_dict,) = parser.parse()
        assert first_dict['new_filename'] == 'b/diff-from/__init__.py'
        assert first_dict['old_filename'] is None
        assert second_dict['new_filename'] == 'b/diff-from/other.py'
        assert second_dict['old_filename'] is None
        assert parser.get_changed_files() == set(['diff-from/__init__.py', 'diff-from/other.py'])
        assert parser.get_lines_by_file() == {}
