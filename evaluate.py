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


def parse(text: str):
    tree = read(tokenize(text))
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


class Lambda:
    def __init__(self, params, body, env):
        self.params = params
        self.body = body
        self.env = env

    def __call__(self, *args):
        return evaluate(self.body, Env(dict(zip(self.params, args)), outer=self.env))

    def __repr__(self):
        return str(self.params) + ' -> ' + str(self.body)


def evaluate(obj, env):
    # print(obj)

    def assign(name, value):
        env[name] = evaluate(value, env)
        return env[name]

    def call(func, *args):
        proc = evaluate(func, env)
        params = [evaluate(arg, env) for arg in args]
        return proc(*params)

    def procedure(*expressions):
        res = None
        for e in expressions:
            res = evaluate(e, env)
        return res

    try:
        if isinstance(obj, list):
            if len(obj) >= 1:
                if obj[0] in ('quote', '\''):
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
                if obj[1] == '<|':
                    return call(obj[0], obj[2])

            return call(obj[0], *obj[1:])

        elif isinstance(obj, str):
            if obj.startswith('"') and obj.endswith('"'):
                return obj[1:-1]
            else:
                return env.find_var(obj)
        else:
            return obj
    except Exception as ex:
        raise RuntimeError('Error on evaluation', (tuple(reversed(ex.args)), obj)) from None


class BindLeft:
    def __init__(self, func, *args):
        self.func = func
        self.args = args

    def __call__(self, *args):
        return self.func(*self.args, *args)


class BindRight:
    def __init__(self, func, *args):
        self.func = func
        self.args = args

    def __call__(self, *args):
        return self.func(*args, *self.args)


def for_each(func, seq):
    for item in seq:
        func(item)


env = Env({
    '+': operator.add,
    '-': operator.sub,
    '*': operator.mul,
    '/': operator.truediv,
    '%': operator.mod,
    '==': operator.eq,
    '!=': operator.ne,
    '<': operator.lt,
    '<=': operator.le,
    '>': operator.gt,
    '>=': operator.ge,
    'len': len,
    'print': print,
    'car': lambda x: x[0],
    'cdr': lambda x: x[1:],
    'cons': lambda x, y: [x] + y,
    'list': lambda *args: list(args),
    'dict': lambda *args: {args[2 * i]: args[2 * i + 1] for i in range(len(args) // 2)},
    '<:': BindLeft,
    ':>': BindRight,
    'seq.map': lambda func, seq: list(map(func, seq)),
    'seq.filter': lambda pred, seq: list(filter(pred, seq)),
    'seq.take': lambda n, seq: list(itertools.islice(seq, None, n)),
    'seq.drop': lambda n, seq: list(itertools.islice(seq, n, None)),
    'seq.take_while': lambda pred, seq: list(itertools.takewhile(pred, seq)),
    'seq.drop_while': lambda pred, seq: list(itertools.dropwhile(pred, seq)),
    'seq.for_each': for_each,
    'seq.zip': lambda lhs, rhs: [[lt, rt] for lt, rt in zip(lhs, rhs)],
    'seq.enumerate': lambda n, seq: [[i, v] for i, v in enumerate(seq)],
    'seq.flatten': lambda seq: list(itertools.chain.from_iterable(seq)),
    'first': operator.itemgetter(0),
    'second': operator.itemgetter(1),

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
        [print "Hello"]
        [sqr := [[x] -> [* x x]]]
        [foo := [
            [:> + 1]
            >> sqr            
            >> [:> / 10]]
        ]
        [3 |> [foo >> print]]    
        [[foo >> print] <| 5]
        [fact := [[n] -> 
            [if [== n 0] 
                1
                [* n [fact [- n 1]]]]]]

        [lst := [list 1 2 3 4 5 6 7 8 16 32]]
        [is_even := [[:> % 2] >> [:> == 0]]]
        [[seq.zip [list 1 2 3 4]  [list 5 6 7 8]] |> [seq.flatten >> [<: seq.for_each print]]]
        [lst |> [<: seq.enumerate 0]]
        ['[1 2 3 4]]
    ]    
    """

try:
    tree = parse(s)
    # display(tree)
    print(evaluate(tree, env))
except Exception as ex:
    for a in ex.args:
        print(a)
