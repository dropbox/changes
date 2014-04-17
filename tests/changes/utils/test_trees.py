from changes.utils.trees import find_trees


def test_find_trees():
    test_names = [
        'foo.bar.bar',
        'foo.bar.biz',
        'foo.biz',
        'blah.brah',
        'blah.blah.blah',
    ]

    result = find_trees(test_names, min_leaves=2)

    assert sorted(result) == [
        ('blah', 2),
        ('foo', 3),
    ]

    result = find_trees(test_names, min_leaves=2, parent='foo')

    assert sorted(result) == [
        ('foo.bar', 2),
        ('foo.biz', 1)
    ]

    result = find_trees(test_names, min_leaves=2, parent='foo.biz')

    assert result == [
    ]
