from changes.utils.trees import build_tree


def test_build_tree():
    test_names = [
        'foo.bar.bar',
        'foo.bar.biz',
        'foo.biz',
        'blah.brah',
        'blah.blah.blah',
    ]

    result = build_tree(test_names, min_children=2)

    assert sorted(result) == ['blah', 'foo']

    result = build_tree(test_names, min_children=2, parent='foo')

    assert sorted(result) == ['foo.bar', 'foo.biz']

    result = build_tree(test_names, min_children=2, parent='foo.biz')

    assert result == set()
