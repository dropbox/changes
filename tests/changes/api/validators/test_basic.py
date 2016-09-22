import pytest
from changes.api.validators.basic import bounded_integer


def test_bounded_integer():
    validator = bounded_integer(0, 10)
    with pytest.raises(ValueError):
        validator("11")

    with pytest.raises(ValueError):
        validator("4.5")

    with pytest.raises(ValueError):
        validator("-3")

    with pytest.raises(ValueError):
        validator("")

    with pytest.raises(ValueError):
        validator("10000")

    # No error expeceted
    validator("0")
    validator("2")
    validator("9")
    validator("10")
