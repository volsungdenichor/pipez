import builtins
import functools
import itertools
import operator

from pipez.functions import to_unary, identity
from pipez.pipe import as_pipeable, Not


def _adjust_selectors(key_selector, value_selector):
    if key_selector is None and value_selector is None:
        return operator.itemgetter(0), operator.itemgetter(1)
    else:
        return to_unary(key_selector) or identity, to_unary(value_selector) or identity


# noinspection PyPep8Naming
class seq:
    @staticmethod
    @as_pipeable
    def len(iterable):
        return sum(1 for _ in iterable)

    @staticmethod
    @as_pipeable
    def map(iterable, func):
        func = to_unary(func)
        return builtins.map(func, iterable)

    bind = map

    @staticmethod
    @as_pipeable
    def take_if(iterable, pred):
        pred = to_unary(pred)
        return builtins.filter(pred, iterable)

    @staticmethod
    @as_pipeable
    def drop_if(iterable, pred):
        pred = to_unary(pred)
        return iterable >> seq.take_if(Not(pred))

    filter = take_if

    @staticmethod
    @as_pipeable
    def slice(iterable, start, stop, step=None):
        return itertools.islice(iterable, start, stop, step)

    @staticmethod
    def take(n):
        return seq.slice(None, n)

    @staticmethod
    def drop(n):
        return seq.slice(n, None)

    @staticmethod
    def step(n):
        return seq.slice(None, None, n)

    @staticmethod
    @as_pipeable
    def take_while(iterable, pred):
        pred = to_unary(pred)
        return itertools.takewhile(pred, iterable)

    @staticmethod
    def take_until(pred):
        return seq.take_while(Not(to_unary(pred)))

    @staticmethod
    @as_pipeable
    def drop_while(iterable, pred):
        pred = to_unary(pred)
        return itertools.dropwhile(pred, iterable)

    @staticmethod
    def drop_until(pred):
        return seq.drop_while(Not(to_unary(pred)))

    @staticmethod
    @as_pipeable
    def enumerate(iterable, start=0):
        return builtins.enumerate(iterable, start=start)

    @staticmethod
    @as_pipeable
    def reverse(iterable):
        return builtins.reversed(iterable)

    @staticmethod
    @as_pipeable
    def sort(iterable, key=None, reverse=False):
        key = to_unary(key)
        return builtins.sorted(iterable, key=key, reverse=reverse)

    @staticmethod
    @as_pipeable
    def zip_with(iterable, other_iterable):
        return builtins.zip(iterable, other_iterable)

    @staticmethod
    @as_pipeable
    def flatten(iterable):
        return itertools.chain.from_iterable(iterable)

    @staticmethod
    def flat_map(func):
        return seq.map(func) >> seq.flatten()

    @staticmethod
    def filter_map(func):
        return seq.map(func) >> seq.filter(lambda item: item is not None)

    @staticmethod
    @as_pipeable
    def tee(iterable, n=2):
        return itertools.tee(iterable, n)

    @staticmethod
    @as_pipeable
    def partition(iterable, pred):
        s1, s2 = iterable >> seq.tee(2)
        return s1 >> seq.take_if(pred), s2 >> seq.drop_if(pred)

    @staticmethod
    @as_pipeable
    def all(iterable, pred=bool):
        return builtins.all(iterable >> seq.map(pred))

    @staticmethod
    @as_pipeable
    def any(iterable, pred=bool):
        return builtins.any(iterable >> seq.map(pred))

    @staticmethod
    @as_pipeable
    def none(iterable, pred=bool):
        return not builtins.any(iterable >> seq.map(pred))

    @staticmethod
    @as_pipeable
    def for_each(iterable, func):
        func = to_unary(func)
        for item in iterable:
            func(item)

    @staticmethod
    @as_pipeable
    def inspect(iterable, func):
        func = to_unary(func)
        for item in iterable:
            func(item)
            yield item

    @staticmethod
    @as_pipeable
    def join(iterable, separator=''):
        return separator.join(iterable >> seq.map(str))

    @staticmethod
    @as_pipeable
    def to(iterable, _class):
        return _class(iterable)

    @staticmethod
    def to_list():
        return seq.to(list)

    @staticmethod
    def to_set():
        return seq.to(set)

    @staticmethod
    def to_tuple():
        return seq.to(tuple)

    @staticmethod
    @as_pipeable
    def to_dict(iterable, key_selector=None, value_selector=None):
        key_selector, value_selector = _adjust_selectors(key_selector, value_selector)
        return {key_selector(item): value_selector(item) for item in iterable}

    @staticmethod
    @as_pipeable
    def to_multidict(iterable, key_selector=None, value_selector=None):
        key_selector, value_selector = _adjust_selectors(key_selector, value_selector)
        res = {}
        for item in iterable:
            res.setdefault(key_selector(item), []).append(value_selector(item))
        return res

    @staticmethod
    @as_pipeable
    def reduce(iterable, func, init):
        return functools.reduce(func, iterable, init)

    @staticmethod
    @as_pipeable
    def sum(iterable):
        return builtins.sum(iterable)

    @staticmethod
    @as_pipeable
    def min(iterable, key=None):
        key = to_unary(key)
        return builtins.min(iterable, key=key)

    @staticmethod
    @as_pipeable
    def max(iterable, key=None):
        key = to_unary(key)
        return builtins.max(iterable, key=key)

    @staticmethod
    @as_pipeable
    def first(iterable):
        return next(iter(iterable), None)

    @staticmethod
    def nth(n):
        return seq.drop(n) >> seq.first()

    @staticmethod
    @as_pipeable
    def extend(iterable, other_iterable):
        return itertools.chain(iterable, other_iterable)
