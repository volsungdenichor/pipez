import operator

from pipez.fmt import fmt
from pipez.pipe import as_pipeable, Pipeable, Function

add = as_pipeable(operator.add)
sub = as_pipeable(operator.sub)
mul = as_pipeable(operator.mul)
truediv = as_pipeable(operator.truediv)
floordiv = as_pipeable(operator.floordiv)
mod = as_pipeable(operator.mod)

neg = Function(operator.neg)


# noinspection PyPep8Naming
class combine(Pipeable):
    def __init__(self, func, *funcs):
        if funcs:
            self.all_funcs = (func,) + funcs

            def result(item):
                return tuple(f(item) for f in self.all_funcs)

            self._func = result
        else:
            self.all_funcs = (func,)
            self._func = func

        self.__name__ = ';'.join(fmt(f) for f in self.all_funcs)

    def __call__(self, item):
        return self._func(item)

    def __repr__(self):
        return self.__name__


# noinspection PyPep8Naming
class get_attr(Pipeable):
    def __init__(self, path):
        self._func = operator.attrgetter(path)

    def __call__(self, arg):
        return self._func(arg)

    def __repr__(self):
        return str(self._func)


# noinspection PyPep8Naming
class get_item(Pipeable):
    def __init__(self, path):
        self._func = operator.itemgetter(path)

    def __call__(self, arg):
        return self._func(arg)

    def __repr__(self):
        return str(self._func)


get_first = Function(operator.itemgetter(0))
get_second = Function(operator.itemgetter(1))
get_key = get_first
get_value = get_second
