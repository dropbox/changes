# Copyright (c) 2007, Armin Ronacher
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 3. All advertising materials mentioning features or use of this software
#    must display the following acknowledgement:
#    This product includes software developed by the <organization>.
# 4. Neither the name of the <organization> nor the
#    names of its contributors may be used to endorse or promote products
#    derived from this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY <COPYRIGHT HOLDER> ''AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from collections import defaultdict
import re
from typing import Optional, List, Set  # NOQA


class FileInfo(object):
    def __init__(self, old_filename, new_filename, chunks, chunk_markers):
        # type: (Optional[str], Optional[str], List[List[LineInfo]], List[str]) -> None
        self.old_filename = old_filename
        self.new_filename = new_filename
        self.chunks = chunks
        self.chunk_markers = chunk_markers

    def __eq__(self, other):
        return ((self.old_filename, self.new_filename, self.chunks, self.chunk_markers) ==
                (other.old_filename, other.new_filename, other.chunks, other.chunk_markers))


class LineInfo(object):
    def __init__(self, old_lineno, new_lineno, action, line, ends_with_newline):
        # type: (int, int, str, str, bool) -> None
        self.old_lineno = old_lineno
        self.new_lineno = new_lineno
        self.action = action
        self.line = line
        self.ends_with_newline = ends_with_newline

    def __eq__(self, other):
        return ((self.old_lineno, self.new_lineno, self.action, self.line, self.ends_with_newline) ==
                (other.old_lineno, other.new_lineno, other.action, other.line, other.ends_with_newline))


class DiffParser(object):
    """
    This is based on code from the open source project, "lodgeit".
    """
    _chunk_re = re.compile(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@')

    def __init__(self, udiff):
        # type: (str) -> None
        """:param udiff:   a text in udiff format"""
        self.lines = udiff.splitlines()

    def _extract_rev(self, line1, line2):
        def _extract(line):
            parts = line.split(None, 1)
            return parts[0], (len(parts) == 2 and parts[1] or None)
        try:
            if line1.startswith('--- ') and line2.startswith('+++ '):
                return _extract(line1[4:]), _extract(line2[4:])
        except (ValueError, IndexError):
            pass
        return (None, None), (None, None)

    def parse(self):
        # type: () -> List[FileInfo]

        # reference: unidiff format by Guido:
        # https://www.artima.com/weblogs/viewpost.jsp?thread=164293
        lineiter = iter(self.lines)
        files = []  # type: List[FileInfo]

        # current_file is only used for git-generated "extended diffs"
        # which are able to express empty file creation and deletion
        current_file = None  # type: Optional[FileInfo]
        try:
            line = lineiter.next()
            while 1:
                if current_file:
                    if line.startswith('diff --git '):
                        files.append(current_file)
                        current_file = None
                    elif line.startswith('deleted file mode '):
                        current_file.new_filename = None
                    elif line.startswith('new file mode '):
                        current_file.old_filename = None
                if not current_file and line.startswith('diff --git '):
                    diff_line = line.strip().split()
                    current_file = FileInfo(
                        old_filename=diff_line[2],
                        new_filename=diff_line[3],
                        chunks=[],
                        chunk_markers=[],
                    )

                if not line.startswith('--- '):
                    line = lineiter.next()
                    continue

                chunks = []  # type: List[List[LineInfo]]
                chunk_markers = []  # type: List[str]
                old, new = self._extract_rev(line, lineiter.next())
                files.append(FileInfo(
                    old_filename=old[0] if old[0] != '/dev/null' else None,
                    new_filename=new[0] if new[0] != '/dev/null' else None,
                    chunks=chunks,
                    chunk_markers=chunk_markers,
                ))
                current_file = None

                line = lineiter.next()
                while line:
                    match = self._chunk_re.match(line)
                    if not match:
                        break

                    lines = []  # type: List[LineInfo]
                    chunks.append(lines)
                    chunk_markers.append(line)

                    old_line, old_end, new_line, new_end = [
                        int(x) for x in match.groups(default='1')
                    ]
                    old_line -= 1
                    new_line -= 1
                    old_end += old_line
                    new_end += new_line
                    line = lineiter.next()

                    while old_line < old_end or new_line < new_end:
                        if line:
                            command, line = line[0], line[1:]
                        else:
                            command = ' '
                        affects_old = affects_new = False

                        if command == '+':
                            affects_new = True
                            action = 'add'
                        elif command == '-':
                            affects_old = True
                            action = 'del'
                        else:
                            affects_old = affects_new = True
                            action = 'unmod'

                        old_line += affects_old
                        new_line += affects_new
                        line_info = LineInfo(
                            old_lineno=affects_old and old_line or 0,
                            new_lineno=affects_new and new_line or 0,
                            action=action,
                            line=line,
                            ends_with_newline=True,
                        )
                        lines.append(line_info)
                        line = lineiter.next()
                        if line == '\ No newline at end of file':
                            line_info.ends_with_newline = False
                            line = lineiter.next()
                assert len(chunks) == len(chunk_markers)

        except StopIteration:
            if current_file:
                files.append(current_file)
            pass

        return files

    def reconstruct_file_diff(self, file_info):
        # type: (FileInfo) -> str
        """Given a FileInfo object as returned by `parse`,
        reconstruct the diff and return it as a string.

        Args:
            file_info (FileInfo) - the same format returned by `parse`
        Returns:
            str - the reconstructed diff
        """
        def no_newline_marker(line):
            # type: (LineInfo) -> str
            if line.ends_with_newline:
                return ''
            else:
                return '\n\ No newline at end of file'
        action_character_dict = {
            'add': '+',
            'del': '-',
            'unmod': ' ',
        }
        if not file_info.chunks:
            return ""
        chunk_strings = []
        for chunk, chunk_marker in zip(file_info.chunks, file_info.chunk_markers):
            lines = [action_character_dict[l.action] + l.line + no_newline_marker(l)
                     for l in chunk]

            chunk_strings.append(
                """{chunk_marker}
{lines}""".format(
                    chunk_marker=chunk_marker,
                    lines='\n'.join(lines)
                )
            )
        diff = """
--- {old_filename}
+++ {new_filename}
{chunks}
""".format(
            old_filename=file_info.old_filename if file_info.old_filename is not None else '/dev/null',
            new_filename=file_info.new_filename if file_info.new_filename is not None else '/dev/null',
            chunks='\n'.join(chunk_strings),
        )
        return diff

    def get_changed_files(self):
        # type: () -> Set[str]
        """Return the set of files affected by this diff.

        This is the union of all non-null 'before' and 'after'
        filenames found in the diff.
        """
        results = set()
        for info in self.parse():
            if info.new_filename:
                results.add(info.new_filename[2:])
            if info.old_filename:
                results.add(info.old_filename[2:])
        return results

    def get_lines_by_file(self):
        # type: () -> Dict[str, Set[int]]
        """Return a dict mapping 'after' filenames to sets of 1-based line numbers.

        The keys are all non-null 'after' filenames in the diff; the
        values refer to the lines that were actually inserted or
        replaced (so not counting lines included in the diff for
        context only), in the numbering after the diff is applied.
        """
        lines_by_file = defaultdict(set)  # type: Dict[str, Set[int]]
        for file_diff in self.parse():
            for diff_chunk in file_diff.chunks:
                if not file_diff.new_filename:
                    continue
                lines_by_file[file_diff.new_filename[2:]].update(
                    d.new_lineno for d in diff_chunk if d.action == 'add'
                )
        return lines_by_file
