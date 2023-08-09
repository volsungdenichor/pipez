from pipez.functions import to_unary
from pipez.pipe import as_pipeable


# noinspection PyPep8Naming
class opt:
    @staticmethod
    @as_pipeable
    def map(obj, func):
        func = to_unary(func)
        return func(obj) if obj is not None else None

    bind = map

    @staticmethod
    @as_pipeable
    def filter(obj, pred):
        pred = to_unary(pred)
        return obj if obj is not None and pred(obj) else None

    @staticmethod
    @as_pipeable
    def value_or(obj, default_value):
        return obj if obj is not None else default_value

    @staticmethod
    @as_pipeable
    def value_or_eval(obj, func):
        return obj if obj is not None else func()

    @staticmethod
    @as_pipeable
    def value_or_raise(obj, exception):
        if obj is not None:
            return obj
        raise opt._to_exception(exception)

    @staticmethod
    def value():
        return opt.value_or_raise('None value')

    @staticmethod
    def _to_exception(exception):
        if isinstance(exception, Exception):
            return exception
        elif isinstance(exception, str):
            return RuntimeError(exception)
        elif callable(exception):
            return opt._to_exception(exception())
