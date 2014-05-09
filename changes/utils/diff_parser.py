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

import re


class DiffParser(object):
    """
    This is based on code from the open source project, "lodgeit".
    """
    _chunk_re = re.compile(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@')

    def __init__(self, udiff):
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
        in_header = True
        header = []
        lineiter = iter(self.lines)
        files = []
        try:
            line = lineiter.next()
            while 1:
                # continue until we found the old file
                if not line.startswith('--- '):
                    if in_header:
                        header.append(line)
                    line = lineiter.next()
                    continue

                if header and all(x.strip() for x in header):
                    # files.append({'is_header': True, 'lines': header})
                    header = []

                in_header = False
                chunks = []
                old, new = self._extract_rev(line, lineiter.next())
                files.append({
                    'is_header': False,
                    'old_filename': old[0],
                    'old_revision': old[1],
                    'new_filename': new[0],
                    'new_revision': new[1],
                    'chunks': chunks,
                })

                line = lineiter.next()
                while line:
                    match = self._chunk_re.match(line)
                    if not match:
                        in_header = True
                        break

                    lines = []
                    chunks.append(lines)

                    old_line, old_end, new_line, new_end = [
                        int(x or 1) for x in match.groups()
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
                        lines.append({
                            'old_lineno': affects_old and old_line or u'',
                            'new_lineno': affects_new and new_line or u'',
                            'action': action,
                            'line': line,
                        })
                        line = lineiter.next()

        except StopIteration:
            pass

        return files
