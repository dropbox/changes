from datetime import datetime

import pytest
from changes.api.validators.datetime import ISODatetime


def test_isodatetime_valid():
    validator = ISODatetime()
    assert validator('2016-09-01T19:46:18.9Z') == datetime(year=2016,
                                                           month=9,
                                                           day=1,
                                                           hour=19,
                                                           minute=46,
                                                           second=18,
                                                           microsecond=900000)


def test_isodatetime_invalid():
    with pytest.raises(ValueError):
        ISODatetime()('invalid')
