def safe_agg(func, sequence, default=None):
    m = default
    for item in sequence:
        if item is None:
            continue
        elif m is None:
            m = item
        elif item:
            m = func(m, item)
    return m
