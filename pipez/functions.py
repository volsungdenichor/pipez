def do_nothing(*_, **__):
    pass


def identity(arg):
    return arg


def to_unary(func):
    import inspect
    from inspect import Parameter

    def is_valid(p):
        return p.kind in (Parameter.POSITIONAL_OR_KEYWORD,) and p.default is p.empty

    if func is None:
        return identity

    try:
        arg_count = sum(1 for p in inspect.signature(func).parameters.values() if is_valid(p))
        if arg_count > 1:
            def result(arg):
                return func(*arg)

            return result
        else:
            return func

    except (TypeError, ValueError):
        return func
