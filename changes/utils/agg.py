def safe_agg(func, sequence, default=None):
    m = None
    for item in sequence:
        if item is None:
            continue
        elif m is None:
            m = item
        else:
            m = func(m, item)
    if m is None:
        m = default
    return m
