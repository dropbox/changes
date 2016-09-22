from typing import Callable  # NOQA


def bounded_integer(lower, upper):
    """Accepts an integer in [lower, upper]."""
    # type: (int, int) -> Callable[str, int]
    def parse(s):
        # type: (str) -> int
        iv = int(s)
        if iv < lower or iv > upper:
            raise ValueError("{} is not in [{}, {}]".format(iv, lower, upper))
        return iv
    return parse
