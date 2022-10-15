def fmt(f):
    if hasattr(f, '__name__'):
        return f.__name__
    if hasattr(f, '__qualname__'):
        return f.__qualname__
    return str(f)


class Pipeable:
    def __rrshift__(self, item):
        return self(item)

    def __rshift__(self, other):
        return Pipe(self, other)


class Pipe(Pipeable):
    def __init__(self, *pipes):
        self.pipes = pipes

    def __call__(self, item):
        for p in self.pipes:
            item = p(item)
        return item

    def __rshift__(self, other):
        if isinstance(other, Pipe):
            return Pipe(*self.pipes, *other.pipes)
        else:
            return Pipe(*self.pipes, other)

    def __repr__(self):
        return '[' + '; '.join(fmt(p) for p in self.pipes) + ']'


def pipeable(func):
    class Wrapper(Pipeable):
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        def __call__(self, arg):
            return func(arg, *self.args, **self.kwargs)

        def __repr__(self):
            return fmt(func) + '(' \
                   + ', '.join(f'{fmt(a)}' for a in self.args) \
                   + ', '.join(f'{k}={fmt(v)}' for k, v in self.kwargs.items()) + ')'

    return Wrapper


fn = Pipe
