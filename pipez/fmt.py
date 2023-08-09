def fmt(f):
    if hasattr(f, '__name__'):
        return f.__name__
    if hasattr(f, '__qualname__'):
        return f.__qualname__
    return str(f)
