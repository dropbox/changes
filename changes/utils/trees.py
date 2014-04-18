from collections import defaultdict


def build_tree(tests, sep='.', min_children=1, parent=''):
    h = defaultdict(set)

    # Build a mapping of prefix => set(children)
    for test in tests:
        segments = test.split(sep)
        for i in xrange(len(segments)):
            prefix = sep.join(segments[:i])
            h[prefix].add(sep.join(segments[:i + 1]))

    # This method expands each node if it has fewer than min_children children.
    # "Expand" here means replacing a node with its children.
    def expand(node='', sep='.', min_children=1):
        # Leave leaf nodes alone.
        if node in h:

            # Expand each child node (depth-first traversal).
            for child in list(h[node]):
                expand(child, sep, min_children)

            # If this node isn't big enough by itself...
            if len(h[node]) < min_children and node:
                parent = h[sep.join(node.split(sep)[:-1])]

                # Replace this node with its expansion.
                parent.remove(node)
                parent.update(h[node])

                del h[node]

    # Expand the tree, starting at the root.
    expand(sep=sep, min_children=min_children)

    if parent:
        return h[parent]
    return h['']
