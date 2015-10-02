from changes.api.serializer import serialize


def test_identity():
    """Verify that serialize returns what we gave it in basic cases."""
    passthrough = [
        None,
        44.2,
        "string",
        [1, 2, 3],
        ["one", 2, 3],
        {'x': 11, 'y': 22},
        {'x': ['yes', 'no'], 'y': {'k': [1, 2, 3]}}
    ]
    for val in passthrough:
        assert serialize(val) == val
