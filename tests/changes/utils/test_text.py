from changes.testutils import TestCase
from changes.utils.text import chunked


class ChunkedTest(TestCase):
    def test_simple(self):
        foo = 'aaa\naaa\naaa\n'

        result = list(chunked(foo, 5))
        assert len(result) == 3
        assert result[0] == 'aaa\n'
        assert result[1] == 'aaa\n'
        assert result[2] == 'aaa\n'

        result = list(chunked(foo, 8))

        assert len(result) == 2
        assert result[0] == 'aaa\naaa\n'
        assert result[1] == 'aaa\n'

        result = list(chunked(foo, 4))

        assert len(result) == 3
        assert result[0] == 'aaa\n'
        assert result[1] == 'aaa\n'
        assert result[2] == 'aaa\n'

        foo = 'a' * 10

        result = list(chunked(foo, 2))
        assert len(result) == 5
        assert all(r == 'aa' for r in result)

        foo = 'aaaa\naaaa'

        result = list(chunked(foo, 3))
        assert len(result) == 4
