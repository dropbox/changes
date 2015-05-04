import re

DIFFUSION_REGEX = re.compile(r'^r[A-Z]+([a-z0-9]+)$')


def might_be_diffusion_iden(text):
    """
    guesses whether text is a diffusion commit name. Right now, it just
    checks the following:
      - starts with lowercase r
      - followed by UPPERCASE CHARACTERS
      - followed by lowercase letters and/or numbers
    Example: rREPOda63b27b7bbd1

    Params:
        text (str): the string to test

    Returns:
        bool: true if its probably a diffusion identifier
    """
    return DIFFUSION_REGEX.match(text) != None


def get_hash_from_diffusion_iden(text):
    """
    Given a string that's very likely a diffusion identifier (see
    might_be_diffusion_iden() above), extract its commit hash/number.

    Params:
        text (str): the diffusion identifier

    Returns:
        str: the commit hash portion of the identifier, or None if the function
        wasn't able to extract it
    """
    match = DIFFUSION_REGEX.match(text)
    if match is None:
        return None
    return match.group(1)
