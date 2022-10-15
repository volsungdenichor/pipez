from pipez.functions import to_unary
from pipez.pipe import pipeable


# noinspection PyPep8Naming
class opt:
    @staticmethod
    @pipeable
    def map(obj, func):
        func = to_unary(func)
        return func(obj) if obj is not None else None

    bind = map

    @staticmethod
    @pipeable
    def filter(obj, pred):
        pred = to_unary(pred)
        return obj if obj is not None and pred(obj) else None

    @staticmethod
    @pipeable
    def value_or(obj, default_value):
        return obj if obj is not None else default_value

    @staticmethod
    @pipeable
    def value_or_eval(obj, func):
        return obj if obj is not None else func()

    @staticmethod
    @pipeable
    def value_or_raise(obj, exception):
        if obj is not None:
            return obj
        raise opt._to_exception(exception)

    @staticmethod
    @pipeable
    def value(obj):
        return obj >> opt.value_or_raise('None value')

    @staticmethod
    def _to_exception(exception):
        if isinstance(exception, Exception):
            return exception
        elif isinstance(exception, str):
            return RuntimeError(exception)
        elif callable(exception):
            return opt._to_exception(exception())
