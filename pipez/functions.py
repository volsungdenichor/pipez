def do_nothing(*_, **__):
    pass


def identity(arg):
    return arg


def negate(func):
    def result(*args, **kwargs):
        return not func(*args, **kwargs)

    return result


# noinspection PyPep8Naming
class apply:
    def __init__(self, func, *funcs):
        if funcs:
            self.all_funcs = (func,) + funcs

            def result(*args, **kwargs):
                return tuple(f(*args, **kwargs) for f in self.all_funcs)

            self._func = result
        else:
            self.all_funcs = (func,)
            self._func = func

        self.__name__ = ';'.join(f.__name__ for f in self.all_funcs)

    def __call__(self, item):
        return self._func(item)

    def __repr__(self):
        return self.__name__


def to_unary(func):
    import inspect
    from inspect import Parameter

    def is_valid(p):
        return p.kind in [Parameter.POSITIONAL_OR_KEYWORD] and p.default is p.empty

    if func is None:
        return identity

    try:
        arg_count = sum(1 for p in inspect.signature(func).parameters.values() if is_valid(p))
        if arg_count > 1:
            return lambda arg: func(*arg)
        else:
            return func

    except (TypeError, ValueError):
        return func
