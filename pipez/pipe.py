from functools import update_wrapper


class Pipe:
    def __init__(self, func, funcs=None):
        self.func = func
        self.funcs = funcs if funcs is not None else (func,)
        update_wrapper(self, func)

    def __call__(self, *args, **kwargs):
        def call(arg):
            return self.func(arg, *args, **kwargs)

        call.__name__ = self.func.__qualname__

        return Pipe(call)

    def __rshift__(self, other):
        assert isinstance(other, Pipe), 'Pipe expected'

        def call(arg):
            return other.func(self.func(arg))

        return Pipe(call, self.funcs + other.funcs)

    def __rrshift__(self, other):
        return self.func(other)

    def __repr__(self):
        def format_func(f):
            return f.__name__

        return f"[{', '.join(map(format_func, self.funcs))}]"
