import functools

from pipez.fmt import fmt


def _flatten(args, getter):
    for a in args:
        yield from getter(a)


class Pipeable:
    def __rshift__(self, other):
        return Pipeline(self, other)

    def __rrshift__(self, other):
        return self(other)

    def __and__(self, other):
        return All(self, other)

    def __or__(self, other):
        return Any(self, other)

    def __invert__(self):
        return Not(self)


class Pipeline(Pipeable):
    def __init__(self, *pipes):
        self._pipes = tuple(_flatten(pipes, lambda p: p._pipes if isinstance(p, Pipeline) else (p,)))

    def __call__(self, arg):
        for p in self._pipes:
            arg = p(arg)

        return arg

    def __str__(self):
        return 'pipeline(' + ', '.join(fmt(p) for p in self._pipes) + ')'


class All(Pipeable):
    def __init__(self, *preds):
        self._preds = tuple(_flatten(preds, lambda p: p._preds if isinstance(p, All) else (p,)))

    def __call__(self, arg):
        return all(p(arg) for p in self._preds)

    def __str__(self):
        return 'all(' + ', '.join(fmt(p) for p in self._preds) + ')'


class Any(Pipeable):
    def __init__(self, *preds):
        self._preds = tuple(_flatten(preds, lambda p: p._preds if isinstance(p, Any) else (p,)))

    def __call__(self, arg):
        return any(p(arg) for p in self._preds)

    def __str__(self):
        return 'any(' + ', '.join(fmt(p) for p in self._preds) + ')'


class Not(Pipeable):
    def __init__(self, pred):
        self._pred = pred

    def __call__(self, arg):
        return not self._pred(arg)

    def __str__(self):
        return 'not(' + fmt(self._pred) + ')'

    def __invert__(self):
        return self._pred


class Function(Pipeable):
    def __init__(self, func, *args, **kwargs):
        self._func = func
        self._args = args
        self._kwargs = kwargs
        self._name = None

    def __call__(self, arg):
        return self._func(arg, *self._args, **self._kwargs)

    def set_name(self, name):
        self._name = name
        return self

    def __str__(self):
        return (self._name or fmt(self._func)) + \
               '(' \
               + ', '.join(fmt(a) for a in self._args) \
               + ', '.join(f'{k}={fmt(v)}' for k, v in self._kwargs.items()) \
               + ')'


def as_pipeable(func=None, *, name=None):
    if func is None:
        return functools.partial(as_pipeable, name=name)
    else:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return Function(func, *args, **kwargs).set_name(name)

        return wrapper

fn = Function