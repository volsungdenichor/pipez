from pipez import Pipe
from pipez.functions import to_unary


@Pipe
def tap(obj, func):
    func = to_unary(func)
    func(obj)
    return obj
