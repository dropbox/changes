from changes.api.serializer import serialize, Crumbler


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


def test_greedy_fetching():
    """
    Test that our greedy algorithm does what we expect. Hopefully, all of the
    other tests will serve to verify that it doesn't mess anything up, so we only
    need to make sure that it actually works
    """

    class Parent(object):
        def __init__(self, data):
            self.data = data

    class Child(Parent):
        pass

    class Baby(Child):
        pass

    # no nonlocal keyword, so use a dictionary as a workaround
    num_extra_attrs_calls = {"value": 0}

    class MyCrumbler(Crumbler):

        def get_extra_attrs_from_db(self, item_list):
            # this is the main assert that makes sure greedy fetching works
            # we create five parent/child/baby objects below, so this function
            # should always be called with five items
            assert len(item_list) == 5, "I didn't batch! item_count=%d" % len(
                item_list)
            num_extra_attrs_calls["value"] += 1

            attrs = {}
            for index, item in enumerate(item_list):
                attrs[item] = (type(item).__name__, index)
            return attrs

        def crumble(self, item, attrs):
            return {
                "class": attrs[0],
                "index": attrs[1],
                "data": item.data,
                "child": item.child if hasattr(item, "child") else None,
                "baby": item.baby if hasattr(item, "baby") else None,
            }

    extended_registry = {
        Parent: MyCrumbler(),
        Child: MyCrumbler(),
        Baby: MyCrumbler()
    }

    parents = []
    for letter in ['a', 'b', 'c', 'd', 'e']:
        child = Child(letter * 2)
        child.baby = Baby(letter * 3)

        parent = Parent(letter)
        parent.child = child

        parents.append(parent)

    serialized = serialize(parents, extended_registry=extended_registry, use_greedy=True)
    assert num_extra_attrs_calls["value"] == 3, "should have batched 3 different objects"

    for index, parent in enumerate(serialized):
        letter = ['a', 'b', 'c', 'd', 'e'][index]

        assert parent["class"] == "Parent"
        assert parent["index"] == index
        assert parent["data"] == letter

        child = parent["child"]
        assert child["class"] == "Child"
        assert child["index"] == index
        assert child["data"] == letter * 2

        baby = child["baby"]
        assert baby["class"] == "Baby"
        assert baby["index"] == index
        assert baby["data"] == letter * 3
