from __future__ import absolute_import, division

import textwrap


def chunked(iterator, chunk_size):
    """
    Given an iterator, chunk it up into ~chunk_size, but be aware of newline
    termination as an intended goal.
    """
    result = ''
    for chunk in iterator:
        result += chunk
        while len(result) >= chunk_size:
            newline_pos = result.rfind('\n', 0, chunk_size)
            if newline_pos == -1:
                newline_pos = chunk_size
            else:
                newline_pos += 1
            yield result[:newline_pos]
            result = result[newline_pos:]
    if result:
        yield result


def nl2br(value):
    return value.replace('\n', '<br>\n')


def break_long_lines(text, *args, **kwargs):
    """
    Wraps the single paragraph in text (a string) so every line is at most
    width characters long. Short lines in text will not be touched.
    """
    result = []
    for line in text.split('\n'):
        result.append(textwrap.fill(line, *args, **kwargs))
    return '\n'.join(result)
