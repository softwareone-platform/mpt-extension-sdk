def find_first(func, iterable, default=None):
    """Find the first item in an iterable that matches a predicate."""
    return next(filter(func, iterable), default)
