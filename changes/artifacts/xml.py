class DelegateParser(object):
    """DelegateParser is a no-op streaming XML parser class intended for
    subclassing.  It allows you to base your final choice of streaming XML
    parser on information from the XML document.  Subclasses should override
    some or all of the `_start`, `_end`, `_data`, and `_close` methods to
    inspect the XML file as its being parsed.  Once the subclass has decided on
    what parser to use, it should call `_set_subparser`. At this point, all
    future parse events will be directed to the subparser, and the `_*` methods
    will no longer be called.  Note that the subparser will begin receiving
    parse events from the point where DelegateParser left off, that is: past
    parse events will *not* be repeated.
    """

    def __init__(self):
        self._subparser = None

    def _set_subparser(self, subparser):
        self._subparser = subparser

    def _start(self, tag, attrib):
        pass

    def _end(self, tag):
        pass

    def _data(self, data):
        pass

    def _close(self):
        return None

    def start(self, tag, attrib):
        if self._subparser:
            self._subparser.start(tag, attrib)
        else:
            self._start(tag, attrib)

    def end(self, tag):
        if self._subparser:
            self._subparser.end(tag)
        else:
            self._end(tag)

    def data(self, data):
        if self._subparser:
            self._subparser.data(data)
        else:
            self._data(data)

    def close(self):
        if self._subparser:
            return self._subparser.close()
        else:
            return self._close()
