from pipez.functions import to_unary
from pipez.pipe import Pipe


class Opt:
    @staticmethod
    @Pipe
    def map(obj, func):
        func = to_unary(func)
        return func(obj) if obj is not None else None

    @staticmethod
    @Pipe
    def filter(obj, pred):
        pred = to_unary(pred)
        return obj if obj is not None and pred(obj) else None

    @staticmethod
    @Pipe
    def value_or(obj, default_value):
        return obj if obj is not None else default_value

    @staticmethod
    @Pipe
    def value_or_eval(obj, func):
        return obj if obj is not None else func()

    @staticmethod
    @Pipe
    def value_or_raise(obj, exception):
        if obj is not None:
            return obj
        raise Opt.to_exception(exception)

    @staticmethod
    @Pipe
    def value(obj):
        return obj >> Opt.value_or_raise('None value')

    @staticmethod
    def to_exception(exception):
        if isinstance(exception, Exception):
            return exception
        elif isinstance(exception, str):
            return RuntimeError(exception)
        elif callable(exception):
            return Opt.to_exception(exception())


opt = Opt
