from functools import update_wrapper


class Pipe:
    def __init__(self, func):
        self.func = func
        update_wrapper(self, func)

    def __call__(self, *args, **kwargs):
        return Pipe(lambda x: self.func(x, *args, **kwargs))

    def __rshift__(self, other):
        assert isinstance(other, Pipe), 'Pipe expected'
        return Pipe(lambda arg: other.func(self.func(arg)))

    def __rrshift__(self, other):
        return self.func(other)
