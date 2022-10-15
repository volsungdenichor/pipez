from pipez.functions import to_unary
from pipez.pipe import pipeable


@pipeable
def tap(obj, func):
    func = to_unary(func)
    func(obj)
    return obj
