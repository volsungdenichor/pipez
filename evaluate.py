import functools
import itertools
import operator
import typing


class Env(dict):
    def __init__(self, values, outer=None):
        self.update(values)
        self.outer = outer

    def find_env(self, k: str):
        if k in self:
            return self
        if self.outer is not None:
            return self.outer.find_env(k)
        else:
            return None

    def find_var(self, k: str):
        e = self.find_env(k)
        if e is not None and k in e:
            return e[k]
        else:
            raise RuntimeError(f'Undefined {k}')


def tokenize(text: str) -> typing.Iterable[str]:
    def replace(s: str) -> typing.Iterable[str]:
        if s.startswith('"') and s.endswith('"'):
            yield s
        else:
            for ch in "[]":
                s = s.replace(ch, f' {ch} ')
            yield from s.split()

    import shlex
    yield from itertools.chain.from_iterable(replace(s) for s in shlex.split(text, posix=False))


def test_tokenize():
    assert list(tokenize("Ala ma kota")) == ["Ala", "ma", "kota"]
    assert list(tokenize("Ala \"ma\" kota")) == ["Ala", "\"ma\"", "kota"]
    assert list(tokenize("Ala \"m[]a\" kota")) == ["Ala", "\"m[]a\"", "kota"]
    assert list(tokenize("[ Ala ][ \"m[]a\" kota]]")) == ["[", "Ala", "]", "[", "\"m[]a\"", "kota", "]", "]"]
    assert list(tokenize("[|123|]")) == ["[", "|", "123", "|", "]"]
    assert list(tokenize("[|]")) == ["[", "|", "]"]


def read(tokens: typing.Iterable[str]):
    def atom(s: str):
        for type_ in (int, float):
            try:
                return type_(s)
            except ValueError:
                pass
        return s

    res = []
    for token in tokens:
        if token == '[':
            res.append(read(tokens))
        elif token == ']':
            break
        else:
            res.append(atom(token))
    return res


def remove_comments(text: str) -> str:
    is_comment = lambda line: line.strip().startswith('#')
    return '\n'.join(line for line in text.split('\n') if not is_comment(line))


def parse(text: str):
    tree = read(tokenize(remove_comments(text)))
    return tree[0]


class Pipe:
    def __init__(self, *funcs):
        self.funcs = funcs

    def __call__(self, *args):
        head, *tail = self.funcs
        res = head(*args)
        for f in tail:
            res = f(res)
        return res

    def __repr__(self):
        return 'Pipe ' + '.'.join(str(f) for f in self.funcs)


class Lambda:
    def __init__(self, params, body, env):
        self.params = params
        self.body = body
        self.env = env

    def __call__(self, *args):
        return evaluate(self.body, Env(dict(zip(self.params, args)), outer=self.env))

    def __repr__(self):
        return 'lambda: ' + str(self.params) + ", " + str(self.body)


def debug(func):
    @functools.wraps(func)
    def result(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as ex:
            raise RuntimeError(f'on running {func}{args}{kwargs}: {ex}')

    return result


def evaluate(obj, env):
    def assign(name, value):
        env[name] = evaluate(value, env)
        return env[name]

    @debug
    def call(func, *args):
        proc = evaluate(func, env)
        params = [evaluate(arg, env) for arg in args]
        return proc(*params)

    def procedure(*expressions):
        res = None
        for e in expressions:
            res = evaluate(e, env)
        return res

    if isinstance(obj, list):
        if len(obj) >= 1:
            if obj[0] == 'quote':
                return obj[1]
            if obj[0] == 'begin':
                return procedure(*obj[1:])
            if obj[0] == 'define':
                return assign(name=obj[1], value=obj[2])
            if obj[0] in ('lambda', 'λ'):
                return Lambda(params=obj[1], body=obj[2], env=env)
            if obj[0] == 'pipe':
                return Pipe(*(evaluate(o, env) for o in obj[1:]))
            if obj[0] == 'compose':
                return Pipe(*reversed(list(evaluate(o, env) for o in obj[1:])))
        if len(obj) >= 2:
            if obj[1] == ':=':
                return assign(name=obj[0], value=obj[2])
            if obj[1] == '->':
                return Lambda(params=obj[0], body=obj[2], env=env)
            if obj[0] == 'if':
                return evaluate(obj[2] if evaluate(obj[1], env) else obj[3], env)
            if all(o == '>>' for i, o in enumerate(obj) if i % 2 != 0):
                return Pipe(*(evaluate(o, env) for i, o in enumerate(obj) if i % 2 == 0))
            if all(o == '<<' for i, o in enumerate(obj) if i % 2 != 0):
                return Pipe(*reversed(list(evaluate(o, env) for i, o in enumerate(obj) if i % 2 == 0)))
            if obj[1] == '|>':
                return call(obj[2], obj[0])
            if obj[0] == '|' and obj[-1] == '|':
                args = obj[1:-1]
                return [evaluate(o, env) for o in args]
            if obj[0] == '{' and obj[-1] == '}':
                args = obj[1:-1]
                return {evaluate(args[2 * i], env): evaluate(args[2 * i + 1], env) for i in range(len(args) // 2)}

        return call(obj[0], *obj[1:])

    elif isinstance(obj, str):
        if obj.startswith('"') and obj.endswith('"'):
            return obj[1:-1]
        else:
            return env.find_var(obj)
    else:
        return obj


class BindLeft:
    def __init__(self, func, *args):
        self.func = func
        self.args = args

    def __call__(self, *args):
        return self.func(*self.args, *args)

    def __repr__(self):
        return 'BindLeft ' + str(self.func) + ' ' + str(self.args)


class BindRight:
    def __init__(self, func, *args):
        self.func = func
        self.args = args

    def __call__(self, *args):
        return self.func(*args, *self.args)

    def __repr__(self):
        return 'BindRight ' + str(self.func) + ' ' + str(self.args)


def for_each(func, seq):
    for item in seq:
        func(item)


class Callable:
    def __init__(self, func, arity=None):
        self.func = func
        self.arity = arity

    def __call__(self, *args):
        if self.arity is not None:
            if len(args) == self.arity:
                return self.func(*args)
            if len(args) < self.arity:
                return Callable(BindLeft(self.func, *args), arity=self.arity - len(args))
            if len(args) > self.arity:
                raise RuntimeError(f'Too many params to {self.func}: expected {self.arity}, got {len(args)}')

        return self.func(*args)

    def __repr__(self):
        return str(self.func)


env = Env({

    '+': Callable(operator.add, arity=2),
    '-': Callable(operator.sub, arity=2),
    '*': Callable(operator.mul, arity=2),
    '/': Callable(operator.truediv, arity=2),
    '%': Callable(operator.mod, arity=2),
    '==': Callable(operator.eq, arity=2),
    '!=': Callable(operator.ne, arity=2),
    '<': Callable(operator.lt, arity=2),
    '<=': Callable(operator.le, arity=2),
    '>': Callable(operator.gt, arity=2),
    '>=': Callable(operator.ge, arity=2),
    'len': Callable(len, arity=1),
    'print': Callable(print, arity=1),
    'apply': Callable(lambda func, lst: func(*lst), arity=2),
    'car': Callable(lambda x: x[0], arity=1),
    'cdr': Callable(lambda x: x[1:], arity=1),
    'cons': Callable(lambda x, y: [x] + y, arity=2),
    'list': Callable(lambda *args: list(args), arity=None),
    'dict': Callable(lambda *args: {args[2 * i]: args[2 * i + 1] for i in range(len(args) // 2)}, arity=None),
    '<:': BindLeft,
    ':>': BindRight,
    'seq.map': Callable(lambda func, seq: list(map(func, seq)), arity=2),
    'seq.filter': Callable(lambda pred, seq: list(filter(pred, seq)), arity=2),
    'seq.take': Callable(lambda n, seq: list(itertools.islice(seq, None, n)), arity=2),
    'seq.drop': Callable(lambda n, seq: list(itertools.islice(seq, n, None)), arity=2),
    'seq.take_while': Callable(lambda pred, seq: list(itertools.takewhile(pred, seq)), arity=2),
    'seq.drop_while': Callable(lambda pred, seq: list(itertools.dropwhile(pred, seq)), arity=2),
    'seq.for_each': Callable(for_each, arity=2),
    'seq.zip': Callable(lambda lhs, rhs: [[lt, rt] for lt, rt in zip(lhs, rhs)], arity=2),
    'seq.enumerate': Callable(lambda n, seq: [[i, v] for i, v in enumerate(seq)], arity=2),
    'seq.flatten': Callable(lambda seq: list(itertools.chain.from_iterable(seq)), arity=1),
    'first': Callable(operator.itemgetter(0), arity=1),
    'second': Callable(operator.itemgetter(1), arity=1),
    'null?': Callable(lambda x: not x, arity=1),
    'and': Callable(lambda *preds: all(p for p in preds), arity=None),
    'or': Callable(lambda *preds: any(p for p in preds), arity=None),
})


def display(obj, indent=0):
    tab = '  ' * indent
    if isinstance(obj, list):
        print(f'{tab}[')
        for item in obj:
            display(item, indent + 1)
        print(f'{tab}]')
    else:
        print(f'{tab}{obj}')


s = \
    """
    [
        begin    
        [lst := [| 1 2 3 4 5 6 7 8 9 10 |]]
        [dct := [{ 
            "a" 3 
            "b" 5 
            "c" lst 
        }]
        [is_even := [[:> % 2] >> [:> == 0]]]
        [lst |> [[seq.filter is_even] >> [seq.map [* 10]]]]
        [pred := [:> >= 5]]
        [pred 4]
        lst
    """

tree = parse(s)
# display(tree)
print(evaluate(tree, env))
