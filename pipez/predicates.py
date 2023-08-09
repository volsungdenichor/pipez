import operator

from pipez.pipe import as_pipeable


# noinspection PyPep8Naming
class predicates:
    @staticmethod
    @as_pipeable
    def eq(arg, value):
        return operator.eq(arg, value)

    @staticmethod
    @as_pipeable
    def ne(arg, value):
        return operator.ne(arg, value)

    @staticmethod
    @as_pipeable
    def lt(arg, value):
        return operator.lt(arg, value)

    @staticmethod
    @as_pipeable
    def le(arg, value):
        return operator.le(arg, value)

    @staticmethod
    @as_pipeable
    def gt(arg, value):
        return operator.gt(arg, value)

    @staticmethod
    @as_pipeable
    def ge(arg, value):
        return operator.ge(arg, value)

    @staticmethod
    @as_pipeable
    def neg(arg, pred):
        return not pred(arg)

    @staticmethod
    @as_pipeable
    def all(arg, *preds):
        return all(p(arg) for p in preds)

    @staticmethod
    @as_pipeable
    def any(arg, *preds):
        return any(p(arg) for p in preds)

    @staticmethod
    @as_pipeable
    def none(arg, *preds):
        return not any(p(arg) for p in preds)

    @staticmethod
    @as_pipeable
    def result_of(arg, func, pred):
        return pred(func(arg))

    @staticmethod
    @as_pipeable
    def len(arg, pred):
        return arg >> predicates.result_of(len, pred)

    @staticmethod
    @as_pipeable
    def is_empty(arg):
        return not arg

    @staticmethod
    @as_pipeable
    def each(arg, pred):
        return all(pred(a) for a in arg)

    @staticmethod
    @as_pipeable
    def contains(arg, pred):
        return any(pred(a) for a in arg)

    @staticmethod
    @as_pipeable
    def is_none(arg):
        return arg is None

    @staticmethod
    @as_pipeable
    def is_not_none(arg):
        return arg is not None
