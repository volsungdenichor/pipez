import builtins
import collections
import functools
import itertools
import operator

from pipez.functions import to_unary, identity, apply, negate
from pipez.pipe import pipeable


def _adjust_selectors(key_selector, value_selector):
    if key_selector is None and value_selector is None:
        return operator.itemgetter(0), operator.itemgetter(1)
    else:
        return to_unary(key_selector) or identity, to_unary(value_selector) or identity


# noinspection PyPep8Naming
class seq:
    @staticmethod
    @pipeable
    def len(iterable):
        return sum(1 for _ in iterable)

    @staticmethod
    @pipeable
    def map(iterable, func):
        func = to_unary(func)
        return builtins.map(func, iterable)

    @staticmethod
    def associate(func):
        func = to_unary(func)
        return seq.map(lambda item: (item, func(item)))

    @staticmethod
    def replace_if(pred, new_value):
        pred = to_unary(pred)
        return seq.map(lambda item: new_value if pred(item) else item)

    @staticmethod
    def replace(old_value, new_value):
        return seq.replace_if(lambda item: item == old_value, new_value)

    @staticmethod
    @pipeable
    def take_if(iterable, pred):
        pred = to_unary(pred)
        return builtins.filter(pred, iterable)

    @staticmethod
    @pipeable
    def drop_if(iterable, pred):
        pred = to_unary(pred)
        return iterable >> seq.take_if(negate(pred))

    filter = take_if

    @staticmethod
    def exclude(other_iterable):
        other_iterable = set(other_iterable)
        return seq.drop_if(lambda x: x in other_iterable)

    @staticmethod
    @pipeable
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
    @pipeable
    def take_while(iterable, pred):
        pred = to_unary(pred)
        return itertools.takewhile(pred, iterable)

    @staticmethod
    def take_until(pred):
        return seq.take_while(negate(to_unary(pred)))

    @staticmethod
    @pipeable
    def drop_while(iterable, pred):
        pred = to_unary(pred)
        return itertools.dropwhile(pred, iterable)

    @staticmethod
    def drop_until(pred):
        return seq.drop_while(negate(to_unary(pred)))

    @staticmethod
    @pipeable
    def enumerate(iterable, start=0):
        return builtins.enumerate(iterable, start=start)

    @staticmethod
    @pipeable
    def reverse(iterable):
        return builtins.reversed(iterable)

    @staticmethod
    @pipeable
    def sort(iterable, key=None, reverse=False):
        key = to_unary(key)
        return builtins.sorted(iterable, key=key, reverse=reverse)

    @staticmethod
    @pipeable
    def zip_with(iterable, other_iterable):
        return builtins.zip(iterable, other_iterable)

    @staticmethod
    @pipeable
    def flatten(iterable):
        return itertools.chain.from_iterable(iterable)

    @staticmethod
    def flat_map(func):
        return seq.map(func) >> seq.flatten()

    @staticmethod
    def filter_map(func):
        return seq.map(func) >> seq.filter(lambda item: item is not None)

    @staticmethod
    @pipeable
    def tee(iterable, n=2):
        return itertools.tee(iterable, n)

    @staticmethod
    @pipeable
    def partition(iterable, pred):
        s1, s2 = iterable >> seq.tee(2)
        return s1 >> seq.take_if(pred), s2 >> seq.drop_if(pred)

    @staticmethod
    @pipeable
    def all(iterable, pred=bool):
        return builtins.all(iterable >> seq.map(pred))

    @staticmethod
    @pipeable
    def any(iterable, pred=bool):
        return builtins.any(iterable >> seq.map(pred))

    @staticmethod
    @pipeable
    def none(iterable, pred=bool):
        return not builtins.any(iterable >> seq.map(pred))

    @staticmethod
    @pipeable
    def for_each(iterable, func):
        func = to_unary(func)
        for item in iterable:
            func(item)

    @staticmethod
    @pipeable
    def inspect(iterable, func):
        func = to_unary(func)
        for item in iterable:
            func(item)
            yield item

    @staticmethod
    @pipeable
    def join(iterable, separator=''):
        return separator.join(iterable >> seq.map(str))

    @staticmethod
    @pipeable
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
    @pipeable
    def to_dict(iterable, key_selector=None, value_selector=None):
        key_selector, value_selector = _adjust_selectors(key_selector, value_selector)
        return {key_selector(item): value_selector(item) for item in iterable}

    @staticmethod
    @pipeable
    def to_multidict(iterable, key_selector=None, value_selector=None):
        key_selector, value_selector = _adjust_selectors(key_selector, value_selector)
        res = {}
        for item in iterable:
            res.setdefault(key_selector(item), []).append(value_selector(item))
        return res

    @staticmethod
    @pipeable
    def reduce(iterable, func, init):
        return functools.reduce(func, iterable, init)

    @staticmethod
    @pipeable
    def sum(iterable):
        return builtins.sum(iterable)

    @staticmethod
    @pipeable
    def min(iterable, key=None):
        key = to_unary(key)
        return builtins.min(iterable, key=key)

    @staticmethod
    @pipeable
    def max(iterable, key=None):
        key = to_unary(key)
        return builtins.max(iterable, key=key)

    @staticmethod
    @pipeable
    def first(iterable):
        return next(iter(iterable), None)

    @staticmethod
    def nth(n):
        return seq.drop(n) >> seq.first()

    @staticmethod
    @pipeable
    def extend(iterable, other_iterable):
        return itertools.chain(iterable, other_iterable)

    @staticmethod
    @pipeable
    def chunk(iterable, chunk_size):
        buffer = []
        for item in iterable:
            buffer.append(item)
            if len(buffer) == chunk_size:
                yield buffer
                buffer = []
        if buffer:
            yield buffer

    @staticmethod
    @pipeable
    def tail(iterable, n):
        return iter(collections.deque(iterable, maxlen=n))

    @staticmethod
    @pipeable
    def slide(iterable, n):
        it = iter(iterable)
        window = collections.deque(itertools.islice(it, n), maxlen=n)
        if len(window) <= n:
            yield tuple(window)
        for x in it:
            window.append(x)
            yield tuple(window)
