import dataclasses
import functools
import itertools
import operator
import typing
from abc import abstractmethod, ABC
from dataclasses import dataclass

Position = tuple[int, int]


@dataclasses.dataclass
class Token:
    text: str
    pos: Position


class Stream:
    def __init__(self, text: str, index: int = None, pos: Position = None):
        self._text = text
        self._index = index or 0
        self.pos = pos or (0, 0)

    def __bool__(self):
        return self._index < len(self._text)

    @property
    def content(self) -> str:
        return self._text[self._index:]

    def peek(self) -> Token:
        return Token(text=self._text[self._index], pos=self.pos)

    def advance(self, count: int):
        res = Stream(text=self._text, index=self._index, pos=self.pos)
        while res and count > 0:
            if res._text[res._index] == '\n':
                res.pos = res.pos[0] + 1, 0
            else:
                res.pos = res.pos[0], res.pos[1] + 1
            res._index += 1
            count -= 1
        return res

    def take(self, count: int) -> tuple[Token, 'Stream']:
        token = Token(self.content[:count], pos=self.pos)
        remainder = self.advance(count)
        return token, remainder

    def __repr__(self):
        return self.content


@dataclass
class ParseResult:
    token: Token
    remainder: Stream
    parser: 'Parser'


class Parser(ABC):
    @abstractmethod
    def parse(self, stream: Stream) -> typing.Optional[ParseResult]:
        ...

    def alias(self, name):
        return Alias(self, name)


class Alias(Parser):
    def __init__(self, parser: Parser, name: str):
        assert isinstance(parser, Parser)
        self._parser = parser
        self._name = name

    def parse(self, stream: Stream) -> typing.Optional[ParseResult]:
        res = self._parser.parse(stream)
        if res is not None:
            return ParseResult(token=res.token,
                               remainder=res.remainder,
                               parser=self)
        else:
            return None

    def __repr__(self):
        return self._name


class Char(Parser):
    def __init__(self, pred: typing.Callable[[str], bool]):
        if callable(pred):
            self._pred = pred
        else:
            self._pred = lambda ch: ch == pred

    def parse(self, stream: Stream) -> typing.Optional[ParseResult]:
        if stream and self._pred(stream.peek().text):
            token, remainder = stream.take(1)
            return ParseResult(token=token,
                               remainder=remainder,
                               parser=self)
        else:
            return None


class String(Parser):
    def __init__(self, string):
        self._string = string

    def parse(self, stream: Stream) -> typing.Optional[ParseResult]:
        if stream and stream.content.startswith(self._string):
            token, remainder = stream.take(len(self._string))
            return ParseResult(token=token,
                               remainder=remainder,
                               parser=self)
        else:
            return None


class Any(Parser):
    def __init__(self, *parsers: Parser):
        assert all(isinstance(p, Parser) for p in parsers)
        self._parsers = parsers

    def parse(self, stream: Stream) -> typing.Optional[ParseResult]:
        for parser in self._parsers:
            res = parser.parse(stream)
            if res is not None:
                return res
        return None


class Seq(Parser):
    def __init__(self, *parsers: Parser):
        assert all(isinstance(p, Parser) for p in parsers)
        self._parsers = parsers

    def parse(self, stream: Stream) -> typing.Optional[ParseResult]:
        remainder = stream
        length = 0
        for parser in self._parsers:
            res = parser.parse(remainder)
            if res is not None:
                remainder = res.remainder
                length += len(res.token.text)
            else:
                return None
        token, remainder = stream.take(length)
        return ParseResult(token=token,
                           remainder=remainder,
                           parser=self)


class Repeat(Parser):
    def __init__(self, parser: Parser, pred: typing.Callable[[int], bool] = None):
        assert isinstance(parser, Parser)
        self._parser = parser
        if pred is not None:
            self._pred = pred
        else:
            self._pred = lambda n: n > 0

    def parse(self, stream: Stream) -> typing.Optional[ParseResult]:
        count = 0
        remainder = stream
        length = 0
        while remainder:
            res = self._parser.parse(remainder)
            if res is not None:
                count += 1
                remainder = res.remainder
                length += len(res.token.text)
            else:
                break

        if self._pred(count):
            token, remainder = stream.take(length)
            return ParseResult(token=token,
                               remainder=remainder,
                               parser=self)
        else:
            return None


class Optional(Parser):
    def __init__(self, parser: Parser):
        assert isinstance(parser, Parser)
        self._parser = parser

    def parse(self, stream: Stream) -> typing.Optional[ParseResult]:
        res = self._parser.parse(stream)
        if res is not None:
            return res
        else:
            return ParseResult(token=Token(text='', pos=stream.pos),
                               remainder=stream,
                               parser=self)


class QuotedString(Parser):
    QUOTATION_MARK = '"'

    def parse(self, stream: Stream) -> typing.Optional[ParseResult]:
        if stream.peek().text != type(self).QUOTATION_MARK:
            return None
        result = type(self).QUOTATION_MARK
        remainder = stream.advance(1)
        while remainder:
            if remainder.content.startswith('\\' + type(self).QUOTATION_MARK):
                result += type(self).QUOTATION_MARK
                remainder = remainder.advance(2)
            elif remainder.content[0] == type(self).QUOTATION_MARK:
                result += type(self).QUOTATION_MARK
                remainder = remainder.advance(1)
                break
            else:
                result += remainder.peek().text
                remainder = remainder.advance(1)
        return ParseResult(token=Token(text=result, pos=stream.peek().pos),
                           remainder=remainder,
                           parser=self)

    def __repr__(self):
        return 'QuotedString'


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


class Pipe:
    def __init__(self, *funcs):
        self.funcs = funcs

    def __call__(self, *args):
        head, *tail = self.funcs
        res = head(*args)
        for f in tail:
            res = f(res)
        return res


class Callable:
    def __init__(self, func, arity=None):
        self.func = func
        self.arity = arity

    def __call__(self, *args):
        if self.arity is not None:
            args_len = len(args)
            if args_len == self.arity:
                return self.func(*args)
            if args_len < self.arity:
                return Callable(BindRight(self.func, *args), arity=self.arity - args_len)
            if args_len > self.arity:
                raise RuntimeError(f'Too many params to {self.func}: expected {self.arity}, got {args_len}')

        return self.func(*args)


def is_quoted_string(s: str) -> bool:
    return s.startswith('"') and s.endswith('"')


class Lambda:
    def __init__(self, params, body, env):
        self.params = params
        self.body = body
        self.env = env

    def __call__(self, *args):
        def result(*a):
            return evaluate(self.body, Env(dict(zip(self.params, a)), outer=self.env))

        return Callable(result, arity=len(self.params))(*args)


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
    '||': Callable(operator.or_, arity=2),
    '&&': Callable(operator.and_, arity=2),
    'len': Callable(len, arity=1),
    'print': Callable(print, arity=1),
    'apply': Callable(lambda func, lst: func(*lst), arity=2),
    'car': Callable(lambda x: x[0], arity=1),
    'cdr': Callable(lambda x: x[1:], arity=1),
    'cons': Callable(lambda x, y: [x] + y, arity=2),
    'bind_lt': BindLeft,
    'bind_rt': BindRight,
    'seq.foldl': Callable(lambda seq, func, init: functools.reduce(func, seq, init), arity=3),
    'seq.foldr': Callable(lambda seq, func, init: functools.reduce(lambda x, y: func(y, x), reversed(seq), init),
                          arity=3),
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


Whitespace = Repeat(Char(str.isspace)).alias('Whitespace')

Literal = Repeat(Char(lambda ch: not (ch in "[]" or ch.isspace()))).alias('Literal')

Sign = Char(lambda c: c in ('+', '-'))
Digit = Char(str.isdigit)

FloatingPoint = Seq(Optional(Sign),
                    Repeat(Digit),
                    Char('.'),
                    Repeat(Digit)).alias('FloatingPoint')

Integer = Seq(Optional(Sign),
              Repeat(Digit)).alias('Integer')

OpeningBracket = Char('[').alias('OpeningBracket')
ClosingBracket = Char(']').alias('ClosingBracket')


def tokenize(text: Stream) -> typing.Iterable[Token]:
    parsers = Any(Whitespace, OpeningBracket, ClosingBracket, FloatingPoint, Integer, QuotedString(), Literal)
    while text:
        res = parsers.parse(text)
        if res is None:
            break
        else:
            text = res.remainder
            if res.parser is not Whitespace:
                yield res.token


def read_tokens(tokens: typing.Iterable[Token]):
    def atom(s: str):
        for type_ in (int, float):
            try:
                return type_(s)
            except ValueError:
                pass
        return s

    res = []
    for token in tokens:
        if token.text == '[':
            res.append(read_tokens(tokens))
        elif token.text == ']':
            break
        else:
            res.append(atom(token.text))
    return res


def load_file(path) -> Stream:
    with open(path, encoding='utf-8') as file:
        return Stream(file.read())


def load(path):
    return read_tokens(tokenize(load_file(path)))[0]


tree = load('code.lisp')

# display(tree)
print(evaluate(tree, env))
