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

            def result(arg):
                return tuple(f(arg) for f in self.all_funcs)

            self._func = result
        else:
            self.all_funcs = (func,)
            self._func = func

        self.__name__ = ';'.join(f.__name__ for f in self.all_funcs)

    def __call__(self, item):
        return self._func(item)

    def __repr__(self):
        return self.__name__


# noinspection PyPep8Naming
class nested_getter:
    def __init__(self, *keys):
        self._keys = keys
        self.__name__ = '.'.join(map(str, self._keys))

    def __call__(self, arg):
        for key in self._keys:
            arg = arg[key]
        return arg

    def __repr__(self):
        return self.__name__


def _split_path(path, delimiter='.'):
    path = path.replace('[', f'{delimiter}[')

    def adjust(value):
        if value.startswith('[') and value.endswith(']'):
            return int(value[1:-1])
        else:
            return value

    chunks = map(adjust, path.split(delimiter))
    return chunks


def getter(*paths, delimiter='.'):
    def create(path):
        if isinstance(path, str):
            return nested_getter(*_split_path(path, delimiter))
        elif isinstance(path, int):
            return nested_getter(path)
        elif isinstance(path, tuple):
            return nested_getter(*path)
        elif callable(path):
            return path

    return apply(*(create(path) for path in paths))


def to_unary(func):
    import inspect
    from inspect import Parameter

    def is_valid(p):
        return p.kind in [Parameter.POSITIONAL_OR_KEYWORD] and p.default is p.empty

    if func is None:
        return identity

    if isinstance(func, (str, int, tuple)):
        return getter(func)

    try:
        if sum(1 for p in inspect.signature(func).parameters.values() if is_valid(p)) > 1:
            return lambda arg: func(*arg)
        else:
            return func

    except (TypeError, ValueError):
        return func
