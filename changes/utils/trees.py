from collections import defaultdict


def find_trees(test_names, sep='.', min_leaves=1, parent=None):
    """
    Group test_names into a trie-like structure returning only parent nodes, and
    discarding any parent nodes which have < min_leaves (so children end up
    expanded).

    i.e.

    min_leaves=1
    [foo.baz, foo.bar, blah] => [foo, blah]

    min_leaves=3
    [foo.baz, foo.bar, blah] => [foo.baz, foo.bar, blah]
    """
    # TODO(dcramer): <-- terrible at Math, pretty sure this can be done better

    grouped = defaultdict(int)

    if parent:
        base_idx = parent.count(sep) + 1
    else:
        base_idx = 0

    if parent:
        test_names = set(t for t in test_names if t.startswith(parent + sep) or t == parent)
    else:
        test_names = set(test_names)

    # build all prefix trees
    for name in test_names:
        if parent:
            key = parent.split(sep)
        else:
            key = []
        for part in name.split(sep)[base_idx:]:
            key.append(part)
            grouped[sep.join(key)] += 1

    # throw away any prefixes that dont have at least `min_nodes`
    for name, num_leaves in grouped.items():
        if num_leaves >= min_leaves or name in test_names:
            continue

        del grouped[name]

    # remove low cardinality duplicates
    sorted_groups = sorted(grouped.items(), key=lambda x: x[1])
    for name, num_leaves in sorted_groups:
        for other_name, other_num_leaves in sorted_groups[::-1]:
            if not name.startswith(other_name + sep):
                continue

            if name == other_name:
                # we've reached our starting point
                break

            # this could already be removed
            grouped.pop(name, None)

    return sorted(grouped.items(), key=lambda x: x[0])
