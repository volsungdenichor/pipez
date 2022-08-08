import builtins
import functools
import itertools
import operator

from pipez.functions import to_unary, identity, apply, negate
from pipez.pipe import Pipe


def _adjust_selectors(key_selector, value_selector):
    if key_selector is None and value_selector is None:
        return operator.itemgetter(0), operator.itemgetter(1)
    else:
        return to_unary(key_selector) or identity, to_unary(value_selector) or identity


class Seq:
    @staticmethod
    @Pipe
    def len(iterable):
        return sum(1 for _ in iterable)

    @staticmethod
    @Pipe
    def map(iterable, *funcs):
        func = apply(*(to_unary(f) for f in funcs))
        return builtins.map(func, iterable)

    @staticmethod
    @Pipe
    def associate(iterable, func):
        func = to_unary(func)
        return iterable >> Seq.map(lambda item: (item, func(item)))

    @staticmethod
    @Pipe
    def replace_if(iterable, pred, new_value):
        pred = to_unary(pred)
        return iterable >> Seq.map(lambda item: new_value if pred(item) else item)

    @staticmethod
    @Pipe
    def replace(iterable, old_value, new_value):
        return iterable >> Seq.map(lambda item: new_value if item == old_value else item)

    @staticmethod
    @Pipe
    def take_if(iterable, pred):
        pred = to_unary(pred)
        return builtins.filter(pred, iterable)

    @staticmethod
    @Pipe
    def drop_if(iterable, pred):
        pred = to_unary(pred)
        return iterable >> Seq.take_if(negate(pred))

    filter = take_if

    @staticmethod
    @Pipe
    def exclude(iterable, other_iterable):
        other_iterable = set(other_iterable)
        return iterable >> Seq.drop_if(lambda x: x in other_iterable)

    @staticmethod
    @Pipe
    def take(iterable, n):
        return itertools.islice(iterable, None, n)

    @staticmethod
    @Pipe
    def drop(iterable, n):
        return itertools.islice(iterable, n, None)

    @staticmethod
    @Pipe
    def step(iterable, n):
        return itertools.islice(iterable, None, None, n)

    @staticmethod
    @Pipe
    def take_while(iterable, pred):
        pred = to_unary(pred)
        return itertools.takewhile(pred, iterable)

    @staticmethod
    @Pipe
    def take_until(iterable, pred):
        pred = negate(to_unary(pred))
        return iterable >> Seq.take_while(pred)

    @staticmethod
    @Pipe
    def drop_while(iterable, pred):
        pred = to_unary(pred)
        return itertools.dropwhile(pred, iterable)

    @staticmethod
    @Pipe
    def drop_until(iterable, pred):
        pred = to_unary(pred)
        return iterable >> Seq.drop_while(negate(pred))

    @staticmethod
    @Pipe
    def enumerate(iterable, start=0):
        return enumerate(iterable, start=start)

    @staticmethod
    @Pipe
    def reverse(iterable):
        return reversed(iterable)

    @staticmethod
    @Pipe
    def sort(iterable, key=None):
        key = to_unary(key)
        return sorted(iterable, key=key)

    @staticmethod
    @Pipe
    def zip_with(iterable, other_iterable):
        return zip(iterable, other_iterable)

    @staticmethod
    @Pipe
    def flatten(iterable):
        return itertools.chain.from_iterable(iterable)

    @staticmethod
    @Pipe
    def flat_map(iterable, func):
        return iterable \
               >> Seq.map(func) \
               >> Seq.flatten()

    @staticmethod
    @Pipe
    def filter_map(iterable, func):
        return iterable \
               >> Seq.map(func) \
               >> Seq.filter(lambda item: item is not None)

    @staticmethod
    @Pipe
    def tee(iterable, n=2):
        return itertools.tee(iterable, n)

    @staticmethod
    @Pipe
    def partition(iterable, pred):
        s1, s2 = iterable >> Seq.tee(2)
        return s1 >> Seq.take_if(pred), s2 >> Seq.drop_if(pred)

    @staticmethod
    @Pipe
    def all(iterable, pred=bool):
        return builtins.all(iterable >> Seq.map(pred))

    @staticmethod
    @Pipe
    def any(iterable, pred=bool):
        return builtins.any(iterable >> Seq.map(pred))

    @staticmethod
    @Pipe
    def none(iterable, pred=bool):
        return not builtins.any(iterable >> Seq.map(pred))

    @staticmethod
    @Pipe
    def for_each(iterable, func):
        func = to_unary(func)
        for item in iterable:
            func(item)

    @staticmethod
    @Pipe
    def inspect(iterable, func):
        for item in iterable:
            func(item)
            yield item

    @staticmethod
    @Pipe
    def join(iterable, separator=''):
        return separator.join(iterable >> Seq.map(str))

    @staticmethod
    @Pipe
    def to_list(iterable):
        return list(iterable)

    @staticmethod
    @Pipe
    def to_set(iterable):
        return set(iterable)

    @staticmethod
    @Pipe
    def to_tuple(iterable):
        return tuple(iterable)

    @staticmethod
    @Pipe
    def to_dict(iterable, key_selector=None, value_selector=None):
        key_selector, value_selector = _adjust_selectors(key_selector, value_selector)
        return {key_selector(item): value_selector(item) for item in iterable}

    @staticmethod
    @Pipe
    def to_multidict(iterable, key_selector=None, value_selector=None):
        key_selector, value_selector = _adjust_selectors(key_selector, value_selector)
        res = {}
        for item in iterable:
            res.setdefault(key_selector(item), []).append(value_selector(item))
        return res

    @staticmethod
    @Pipe
    def reduce(iterable, func, init):
        return functools.reduce(func, iterable, init)

    @staticmethod
    @Pipe
    def sum(iterable):
        return builtins.sum(iterable)

    @staticmethod
    @Pipe
    def min(iterable, key=None):
        key = to_unary(key)
        return builtins.min(iterable, key=key)

    @staticmethod
    @Pipe
    def max(iterable, key=None):
        key = to_unary(key)
        return builtins.max(iterable, key=key)

    @staticmethod
    @Pipe
    def first(iterable):
        return next(iter(iterable), None)

    @staticmethod
    @Pipe
    def nth(iterable, n):
        return iterable >> Seq.drop(n) >> Seq.first()

    @staticmethod
    @Pipe
    def chain(iterable, other_iterable):
        return itertools.chain(iterable, other_iterable)

    @staticmethod
    @Pipe
    def chunk(iterable, chunk_size):
        buffer = []
        for item in iterable:
            buffer.append(item)
            if len(buffer) == chunk_size:
                yield buffer
                buffer = []
        if buffer:
            yield buffer


seq = Seq
