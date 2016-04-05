import mock

from changes.api.serializer import Crumbler, new_serialize as serialize
from changes.testutils import TestCase


class SerializeTest(TestCase):
    def test_identity(self):
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

    class _Foo(object):
        def __init__(self, inner):
            self.inner = inner

    class _Bar(object):
        def __init__(self, inner):
            self.inner = inner

    def _setup_crumblers(self, get_crumbler):
        """
        Given a mocked get_crumbler, sets it up with crumblers for the _Foo
        and _Bar classes.
        Returns:
            tuple of (foo_crumbler, bar_crumbler)
        """
        foo_crumbler = mock.Mock(spec=Crumbler())
        foo_crumbler.crumble.side_effect = lambda item, attrs: item.inner
        foo_crumbler.get_extra_attrs_from_db.return_value = {}
        bar_crumbler = mock.Mock(spec=Crumbler())
        bar_crumbler.crumble.side_effect = lambda item, attrs: item.inner
        bar_crumbler.get_extra_attrs_from_db.return_value = {}
        crumbler_mapping = {SerializeTest._Foo: foo_crumbler, SerializeTest._Bar: bar_crumbler}
        get_crumbler.side_effect = lambda item, registry: crumbler_mapping[item.__class__]

        return (foo_crumbler, bar_crumbler)

    def _assert_crumble_called_for(self, crumbler, items, any_order=False, attrs=None):
        """
        Asserts that crumbler.crumble() was called on exactly the given list of items, and no others.
        Args:
            crumbler: the mocked crumbler in question.
            items: list of objects, each of which we expect a crumble() call for.
            any_order: if False, items is assumed to be in the expected order of calls.
            attrs: expected extra attributes argument to crumble (default None)
        """
        crumbler.crumble.assert_has_calls([mock.call(item, attrs)
                                           for item in items], any_order=any_order)
        assert crumbler.crumble.call_count == len(items)

    @mock.patch('changes.api.serializer.base.get_crumbler')
    def test_list(self, get_crumbler):
        foo_crumbler, bar_crumbler = self._setup_crumblers(get_crumbler)

        item1 = SerializeTest._Foo('foo')
        item2 = SerializeTest._Bar('bar')
        item3 = SerializeTest._Foo('foo2')
        ret = serialize([item1, item2, item3, 'passthrough'])
        assert ret == ['foo', 'bar', 'foo2', 'passthrough']
        foo_crumbler.get_extra_attrs_from_db.assert_called_once_with({item1, item3})
        bar_crumbler.get_extra_attrs_from_db.assert_called_once_with({item2})

        self._assert_crumble_called_for(foo_crumbler, [item1, item3])
        self._assert_crumble_called_for(bar_crumbler, [item2])

    @mock.patch('changes.api.serializer.base.get_crumbler')
    def test_dict(self, get_crumbler):
        foo_crumbler, bar_crumbler = self._setup_crumblers(get_crumbler)

        item1 = SerializeTest._Foo('foo')
        item2 = SerializeTest._Bar('bar')
        item3 = SerializeTest._Foo('foo2')
        item4 = SerializeTest._Bar('baz')
        ret = serialize({item1: item2, 'otherkey': item3, item4: 'otherval'})
        assert ret == {'foo': 'bar', 'otherkey': 'foo2', 'baz': 'otherval'}
        foo_crumbler.get_extra_attrs_from_db.assert_called_once_with({item1, item3})
        bar_crumbler.get_extra_attrs_from_db.assert_called_once_with({item4, item2})

        # in the current implementation, keys are crumbled before values, so these
        # have a defined order, but doesn't seem worth relying on that behavior
        # in our tests.
        self._assert_crumble_called_for(foo_crumbler, [item1, item3], any_order=True)
        self._assert_crumble_called_for(bar_crumbler, [item4, item2], any_order=True)

    @mock.patch('changes.api.serializer.base.get_crumbler')
    def test_recursive(self, get_crumbler):
        foo_crumbler, bar_crumbler = self._setup_crumblers(get_crumbler)

        item1 = SerializeTest._Bar(['baz'])
        item2 = SerializeTest._Foo(item1)
        item3 = SerializeTest._Foo({'foo': ['thing', item2, 'other'],
                                   'otherkey': 'otherval'})
        item4 = SerializeTest._Bar('bar')
        ret = serialize([item3, item4])
        assert ret == [{'foo': ['thing', ['baz'], 'other'], 'otherkey': 'otherval'}, 'bar']
        # We won't be able to see item2 until we've unwrapped item3, so in this
        # case, we do expect separate calls to `get_extra_attrs_from_db`.
        foo_crumbler.get_extra_attrs_from_db.assert_has_calls([mock.call({item3}),
                                                               mock.call({item2})])
        bar_crumbler.get_extra_attrs_from_db.assert_has_calls([mock.call({item4}),
                                                               mock.call({item1})])

        self._assert_crumble_called_for(foo_crumbler, [item3, item2])
        self._assert_crumble_called_for(bar_crumbler, [item4, item1])

    @mock.patch('changes.api.serializer.base.get_crumbler')
    def test_embedded(self, get_crumbler):
        foo_crumbler, bar_crumbler = self._setup_crumblers(get_crumbler)

        item1 = SerializeTest._Bar('bar')
        item2 = SerializeTest._Foo({'foo': item1})
        item3 = SerializeTest._Bar('baz')
        item4 = SerializeTest._Foo({'fuzz': item3})
        ret = serialize([item2, item4])
        assert ret == [{'foo': 'bar'}, {'fuzz': 'baz'}]
        foo_crumbler.get_extra_attrs_from_db.assert_called_once_with({item2, item4})
        bar_crumbler.get_extra_attrs_from_db.assert_called_once_with({item1, item3})

        self._assert_crumble_called_for(foo_crumbler, [item2, item4])
        self._assert_crumble_called_for(bar_crumbler, [item1, item3])

    @mock.patch('changes.api.serializer.base.get_crumbler')
    def test_embedded_get_extra_attrs(self, get_crumbler):
        foo_crumbler, bar_crumbler = self._setup_crumblers(get_crumbler)

        item1 = SerializeTest._Bar('bar')
        item2 = SerializeTest._Foo('foo')
        item3 = SerializeTest._Foo('fuzz')

        foo_crumbler.crumble.side_effect = lambda item, attrs: [item.inner, attrs['foo']]
        attrs = {'foo': item1}
        foo_crumbler.get_extra_attrs_from_db.return_value = {item2: attrs,
                                                             item3: attrs}

        ret = serialize([item2, item3])
        assert ret == [['foo', 'bar'], ['fuzz', 'bar']]
        foo_crumbler.get_extra_attrs_from_db.assert_called_once_with({item2, item3})
        bar_crumbler.get_extra_attrs_from_db.assert_called_once_with({item1})

        self._assert_crumble_called_for(foo_crumbler, [item2, item3], attrs=attrs)
        # we don't currently batch crumble() calls for the same object, so
        # crumble() will actually get called twice here. The assumption is that
        # crumble() itself is cheap, while get_extra_attrs_from_db() is not.
        self._assert_crumble_called_for(bar_crumbler, [item1, item1])
