from pipez.functions import to_unary
from pipez.pipe import as_pipeable


@as_pipeable
def tap(obj, func):
    func = to_unary(func)
    func(obj)
    return obj
