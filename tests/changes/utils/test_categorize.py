import textwrap
import unittest

from changes.experimental.categorize import parse_rules, _parse_rule, categorize, ParseError


class TestCategorize(unittest.TestCase):
    def test_parse_empty_rule(self):
        self.assertEqual(_parse_rule(''), None)
        self.assertEqual(_parse_rule(' \n'), None)
        self.assertEqual(_parse_rule('# foo \n'), None)
        self.assertEqual(_parse_rule(' # foo \n'), None)

    def test_parse_rule(self):
        self.assertEqual(_parse_rule('tag::regex'), ('tag', '', 'regex'))
        self.assertEqual(_parse_rule(' x-fail : proj : test error '),
                         ('x-fail', 'proj', 'test error'))
        self.assertEqual(_parse_rule(' tag : proj-2 : regex :: '), ('tag', 'proj-2', 'regex ::'))

    def test_parse_rule_with_quoted_regexp(self):
        self.assertEqual(_parse_rule('tag::"reg\'ex"'), ('tag', '', "reg'ex"))
        self.assertEqual(_parse_rule("tag:: 'reg\"ex' "), ('tag', '', 'reg"ex'))
        self.assertEqual(_parse_rule("tag:: 'reg\\'ex' "), ('tag', '', "reg'ex"))
        self.assertEqual(_parse_rule("tag:: r'reg\\'ex' "), ('tag', '', "reg\\'ex"))

    def test_parse_rules(self):
        self.assertEqual(parse_rules(''), [])
        data = dedent('''\
            # comment

            tag::^ERROR$

            tag2:project:\\[error\\]
            ''')
        self.assertEqual(parse_rules(data),
                         [('tag', '', '^ERROR$'),
                          ('tag2', 'project', r'\[error\]')])

    def test_categorize_general_rule(self):
        rules = [('tag', '', 'error')]
        self.assertEqual(categorize('proj', rules, '.. error ..'), ({'tag'}, {'tag'}))
        self.assertEqual(categorize('proj', rules, '.. Error ..'), (set(), {'tag'}))

    def test_categorize_general_rule_two_tags(self):
        rules = [('tag', '', 'error'),
                 ('tag2', '', 'fail')]
        tags = {'tag', 'tag2'}
        self.assertEqual(categorize('proj', rules, '.. error .. fail'), ({'tag', 'tag2'}, tags))
        self.assertEqual(categorize('proj', rules, '.. fail ..'), ({'tag2'}, tags))
        self.assertEqual(categorize('proj', rules, '.. error ..'), ({'tag'}, tags))
        self.assertEqual(categorize('proj', rules, '.. ok ..'), (set(), tags))

    def test_categorize_project_rule(self):
        rules = [('tag2', 'proj', 'error')]
        self.assertEqual(categorize('proj', rules, '.. error ..'), ({'tag2'}, {'tag2'}))
        self.assertEqual(categorize('proj2', rules, '.. error ..'), (set(), set()))

    def test_categorize_full_line_regexp(self):
        rules = [('tag2', 'proj', '^error$')]
        self.assertEqual(categorize('proj', rules, 'error'), ({'tag2'}, {'tag2'}))
        self.assertEqual(categorize('proj', rules, '\nerror\n'), ({'tag2'}, {'tag2'}))
        self.assertEqual(categorize('proj', rules, 'xerror'), (set(), {'tag2'}))
        self.assertEqual(categorize('proj', rules, '\nerrorx\n'), (set(), {'tag2'}))

    def test_categorize_full_line_regexp_cr_lf(self):
        rules = [('tag', 'proj', '^error$')]
        self.assertEqual(categorize('proj', rules, '\r\nerror\r\n'), ({'tag'}, {'tag'}))

    def test_categorize_match_newline(self):
        rules = [('atag', 'aproj', 'line1.*line2')]
        self.assertEqual(categorize('aproj', rules, 'line1\n\nline2'), ({'atag'}, {'atag'}))

    def test_parse_error(self):
        with self.assertRaisesRegexp(ParseError, 'file.ext, line 2: syntax error'):
            parse_rules('foo::bar\n'
                        'foo:bar', path='file.ext')

    def test_quotes_parse_error(self):
        with self.assertRaisesRegexp(ParseError, 'file.ext, line 1: mismatched quotes'):
            parse_rules('foo::"bar\n', path='file.ext')

    def test_quotes_parse_error_2(self):
        with self.assertRaisesRegexp(ParseError, 'file.ext, line 1: invalid Python string literal'):
            parse_rules("foo::bar' \n", path='file.ext')

    def test_quotes_parse_error_3(self):
        with self.assertRaisesRegexp(ParseError, 'file.ext, line 1: invalid Python string literal'):
            parse_rules("foo::'b'ar' \n", path='file.ext')

    def test_unicode_regexp(self):
        with self.assertRaisesRegexp(ParseError, 'file.ext, line 1: syntax error'):
            parse_rules("foo::u'foo'", path='file.ext')

    def test_regex_parse_error(self):
        with self.assertRaisesRegexp(ParseError,
                                     'file.ext, line 1: unexpected end of regular expression'):
            parse_rules('foo::[x', path='file.ext')


def dedent(string):
    return textwrap.dedent(string)
