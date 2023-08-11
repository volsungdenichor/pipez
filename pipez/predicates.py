import builtins
import operator

from pipez import pipe
from pipez.functions import to_unary
from pipez.pipe import as_pipeable, Function, Pipeline

eq = as_pipeable(operator.eq)
ne = as_pipeable(operator.ne)
lt = as_pipeable(operator.lt)
gt = as_pipeable(operator.gt)
le = as_pipeable(operator.le)
ge = as_pipeable(operator.ge)

all_of = pipe.All
any_of = pipe.Any
not_ = pipe.Not

is_none = Function(lambda arg: arg is None)
always = Function(lambda _: True)
never = Function(lambda _: False)


def result_of(func, pred):
    return Pipeline(func, pred)


def size_is(pred):
    return result_of(len, pred)


is_empty = size_is(0)


@as_pipeable
def each(arg, pred):
    pred = to_unary(pred)
    return builtins.all(pred(a) for a in arg)


@as_pipeable
def contains(arg, pred):
    pred = to_unary(pred)
    return builtins.any(pred(a) for a in arg)


@as_pipeable
def has_prefix(arg, prefix):
    return arg[:len(prefix)] == prefix


@as_pipeable
def has_suffix(arg, suffix):
    return arg[-len(suffix):] == suffix


@as_pipeable
def contains_subrange(arg, sub):
    arg_len = len(arg)
    sub_len = len(sub)
    return arg_len >= sub_len and builtins.any(arg[i:i + sub_len] == sub for i in range(0, arg_len - sub_len + 1))
