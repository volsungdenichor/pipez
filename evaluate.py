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


class Bind:
    def __init__(self, func, *args):
        self.func = func
        self.args = args


class BindLeft(Bind):
    def __init__(self, func, *args):
        super().__init__(func, *args)

    def __call__(self, *args):
        return self.func(*self.args, *args)


class BindRight(Bind):
    def __init__(self, func, *args):
        super().__init__(func, *args)

    def __call__(self, *args):
        return self.func(*args, *self.args)


class Callable:
    def __init__(self, func, arity=None):
        self.func = func
        self.arity = arity

    def __call__(self, *args):
        if self.arity is not None:
            if len(args) == self.arity:
                return self.func(*args)
            if len(args) < self.arity:
                return Callable(BindRight(self.func, *args), arity=self.arity - len(args))
            if len(args) > self.arity:
                raise RuntimeError(f'Too many params to {self.func}: expected {self.arity}, got {len(args)}')

        return self.func(*args)

    def __repr__(self):
        return str(self.func)


class Pipe:
    def __init__(self, *funcs):
        self.funcs = funcs

    def __call__(self, *args):
        head, *tail = self.funcs
        res = head(*args)
        for f in tail:
            res = f(res)
        return res


def is_quoted_string(s: str) -> bool:
    return s.startswith('"') and s.endswith('"')


def tokenize(text: str) -> typing.Iterable[str]:
    def replace(s: str) -> typing.Iterable[str]:
        if is_quoted_string(s):
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
    assert list(tokenize("[| 123 |]")) == ["[", "|", "123", "|", "]"]
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
    tokens = tokenize(remove_comments(text))
    tree = read(tokens)
    return tree[0]


class Lambda:
    def __init__(self, params, body, env):
        self.params = params
        self.body = body
        self.env = env

    def __call__(self, *args):
        def result(*a):
            return evaluate(self.body, Env(dict(zip(self.params, a)), outer=self.env))

        return Callable(result, arity=len(self.params))(*args)

    def __repr__(self):
        return 'lambda: ' + str(self.params) + ", " + str(self.body)


def get_delimited(symbol, args):
    if all(a == symbol for i, a in enumerate(args) if i % 2 != 0):
        return [a for i, a in enumerate(args) if i % 2 == 0]
    else:
        return None


def evaluate(obj, env):
    if isinstance(obj, list):
        if len(obj) >= 1:
            if obj[0] == 'quote':
                return obj[1]
            if obj[0] == 'begin':
                res = None
                for e in obj[1:]:
                    res = evaluate(e, env)
                return res
        if len(obj) >= 2:
            if obj[1] == '..':
                return list(range(evaluate(obj[0], env), 1 + evaluate(obj[2], env)))
            if obj[1] == ':=':
                name, value = obj[0], obj[2]
                env[name] = evaluate(value, env)
                return env[name]
            if obj[1] == '->':
                return Lambda(params=obj[0], body=obj[2], env=env)
            if obj[0] == 'if':
                return evaluate(obj[2] if evaluate(obj[1], env) else obj[3], env)
            if (items := get_delimited('>>', obj)) is not None:
                return Pipe(*(evaluate(it, env) for it in items))
            if (items := get_delimited('|>', obj)) is not None:
                res, *funcs = items
                return Pipe(*(evaluate(f, env) for f in funcs))(evaluate(res, env));
            if obj[0] == '|' and obj[-1] == '|':
                args = obj[1:-1]
                return [evaluate(o, env) for o in args]
            if obj[0] == '{' and obj[-1] == '}':
                args = obj[1:-1]
                return {evaluate(args[2 * i], env): evaluate(args[2 * i + 1], env) for i in range(len(args) // 2)}

        try:
            func, *args = obj
            proc = evaluate(func, env)
            params = [evaluate(arg, env) for arg in args]
            return proc(*params)
        except Exception as ex:
            raise RuntimeError(f'Error on evaulation of {func}: {ex}')

    elif isinstance(obj, str):
        if is_quoted_string(obj):
            return obj[1:-1]
        else:
            return env.find_var(obj)
    else:
        return obj


def for_each(func, seq):
    for item in seq:
        func(item)


class Ap:
    def __init__(self, *funcs):
        self.funcs = funcs

    def __call__(self, arg):
        return [f(arg) for f in self.funcs]


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
    'seq.map': Callable(lambda seq, func: list(map(func, seq)), arity=2),
    'seq.filter': Callable(lambda seq, pred: list(filter(pred, seq)), arity=2),
    'seq.take': Callable(lambda seq, n: list(itertools.islice(seq, None, n)), arity=2),
    'seq.drop': Callable(lambda seq, n: list(itertools.islice(seq, n, None)), arity=2),
    'seq.take_while': Callable(lambda seq, pred: list(itertools.takewhile(pred, seq)), arity=2),
    'seq.drop_while': Callable(lambda seq, pred: list(itertools.dropwhile(pred, seq)), arity=2),
    'seq.for_each': Callable(for_each, arity=2),
    'seq.zip': Callable(lambda lhs, rhs: [[lt, rt] for lt, rt in zip(lhs, rhs)], arity=2),
    'seq.enumerate': Callable(lambda seq, n: [[i, v] for i, v in enumerate(seq)], arity=2),
    'seq.flatten': Callable(lambda seq: list(itertools.chain.from_iterable(seq)), arity=1),
    'seq.join': Callable(lambda seq, sep: sep.join(str(v) for v in seq), arity=2),
    'first': Callable(operator.itemgetter(0), arity=1),
    'second': Callable(operator.itemgetter(1), arity=1),
    'null?': Callable(lambda x: not x, arity=1),
    'str': Callable(str, arity=1),
    'True': True,
    'False': False,
    'and': Callable(lambda arg, preds: all(p(arg) for p in preds), arity=2),
    'or': Callable(lambda arg, preds: any(p(arg) for p in preds), arity=2),
    '@': Callable(lambda arg, key: arg[key], arity=2),
    'in': Callable(lambda arg, key: key in arg, arity=2),
    'ap': Ap,
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


def load(path):
    with open(path, encoding='utf-8') as file:
        return '\n'.join(file)


tree = parse(load('code.lisp'))
# display(tree)
print(evaluate(tree, env))
