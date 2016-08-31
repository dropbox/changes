import mock
import sys

from changes.testutils.cases import TestCase
from changes.utils.collect_bazel_targets import main


class CollectBazelTargetTestCase(TestCase):

    def test_simple(self):
        with mock.patch('subprocess.check_output') as mock_check_output:
            mock_check_output.side_effect = ['''
//aa/bb/cc:test
//aa/abc:test
''', '''
/home/ubuntu/bazel-testlogs
'''
                                             ]
            with mock.patch('json.dump') as mock_dump:
                ret = main(
                    ['/tmp/testroot', '//aa/bb/cc/...,//aa/abc:all_targets', '', '3'])
        assert ret == 0
        assert mock_check_output.call_args_list == [mock.call([
            '/usr/bin/bazel',
            '--nomaster_blazerc',
            '--blazerc=/dev/null',
            '--output_user_root=/tmp/testroot',
            '--batch',
            'query',
            '''let t = tests(//aa/bb/cc/... + //aa/abc:all_targets) in ($t )''',
        ]), mock.call([
            '/usr/bin/bazel',
            '--nomaster_blazerc',
            '--blazerc=/dev/null',
            '--output_user_root=/tmp/testroot',
            '--batch',
            'info',
            'bazel-testlog',
        ])]
        mock_dump.assert_called_once_with({
            'cmd': '/usr/bin/bazel --output_user_root=/tmp/testroot test --jobs=3 {test_names}',
            'tests': ['//aa/bb/cc:test', '//aa/abc:test'],
            'artifact_search_path': '/home/ubuntu/bazel-testlogs',
            'artifacts': ['*.xml'],
        }, sys.stdout)

    def test_with_exludes(self):
        with mock.patch('subprocess.check_output') as mock_check_output:
            mock_check_output.side_effect = ['''
//aa/bb/cc:test
//aa/abc:test
''', '''
/home/ubuntu/bazel-testlogs
'''
                                             ]
            with mock.patch('json.dump') as mock_dump:
                ret = main(
                    ['/tmp/testroot', '//aa/bb/cc/...,//aa/abc:all_targets', 'exclude1,exclude2', '3'])
        assert ret == 0
        assert mock_check_output.call_args_list == [mock.call([
            '/usr/bin/bazel',
            '--nomaster_blazerc',
            '--blazerc=/dev/null',
            '--output_user_root=/tmp/testroot',
            '--batch',
            'query',
            '''let t = tests(//aa/bb/cc/... + //aa/abc:all_targets) in ($t except (attr("tags", "(\[| )exclude1(\]|,)", $t)) except (attr("tags", "(\[| )exclude2(\]|,)", $t)))''',
        ]), mock.call([
            '/usr/bin/bazel',
            '--nomaster_blazerc',
            '--blazerc=/dev/null',
            '--output_user_root=/tmp/testroot',
            '--batch',
            'info',
            'bazel-testlog',
        ])]
        mock_dump.assert_called_once_with({
            'cmd': '/usr/bin/bazel --output_user_root=/tmp/testroot test --jobs=3 {test_names}',
            'tests': ['//aa/bb/cc:test', '//aa/abc:test'],
            'artifact_search_path': '/home/ubuntu/bazel-testlogs',
            'artifacts': ['*.xml'],
        }, sys.stdout)
