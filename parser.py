import dataclasses
import typing
from abc import abstractmethod, ABC
from dataclasses import dataclass


@dataclasses.dataclass
class Token:
    text: str
    pos: tuple[int, int]


class Text:
    def __init__(self, text: str):
        self._text = text
        self._index = 0
        self._pos = 0, 0

    def __bool__(self):
        return self._index < len(self._text)

    def text(self) -> str:
        return self._text[self._index:]

    def peek(self) -> Token:
        return Token(text=self._text[self._index], pos=self._pos)

    def read(self) -> Token:
        res = self.peek()
        if self._text[self._index] == '\n':
            self._pos = 0, self._pos[1] + 1
        else:
            self._pos = self._pos[0] + 1, self._pos[1]
        self._index += 1
        return res


@dataclass
class ParseResult:
    text: str
    remainder: str
    parser: 'Parser'


class Parser(ABC):
    @abstractmethod
    def parse(self, text: str) -> typing.Optional[ParseResult]:
        ...

    def alias(self, name):
        return Alias(self, name)

    def create_result(self, text: str, remainder: str) -> ParseResult:
        return ParseResult(text=text, remainder=remainder, parser=self)


class Alias(Parser):
    def __init__(self, parser: Parser, name: str):
        assert isinstance(parser, Parser)
        self._parser = parser
        self._name = name

    def parse(self, text: str) -> typing.Optional[ParseResult]:
        res = self._parser.parse(text)
        if res is not None:
            return self.create_result(text=res.text, remainder=res.remainder)
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

    def parse(self, text: str) -> typing.Optional[ParseResult]:
        if text and self._pred(text[0]):
            return self.create_result(text=text[0], remainder=text[1:])
        else:
            return None


class String(Parser):
    def __init__(self, string):
        self._string = string

    def parse(self, text: str) -> typing.Optional[ParseResult]:
        if text and text.startswith(self._string):
            length = len(self._string)
            return self.create_result(text=text[:length], remainder=text[length:])
        else:
            return None


class Any(Parser):
    def __init__(self, *parsers: Parser):
        assert all(isinstance(p, Parser) for p in parsers)
        self._parsers = parsers

    def parse(self, text: str) -> typing.Optional[ParseResult]:
        for parser in self._parsers:
            res = parser.parse(text)
            if res is not None:
                return res
        return None


class Seq(Parser):
    def __init__(self, *parsers: Parser):
        assert all(isinstance(p, Parser) for p in parsers)
        self._parsers = parsers

    def parse(self, text: str) -> typing.Optional[ParseResult]:
        remainder = text
        result = ''
        for parser in self._parsers:
            res = parser.parse(remainder)
            if res is not None:
                remainder = res.remainder
                result += res.text
            else:
                return None
        return self.create_result(text=result, remainder=remainder)


class Repeat(Parser):
    def __init__(self, parser: Parser, pred: typing.Callable[[int], bool] = None):
        assert isinstance(parser, Parser)
        self._parser = parser
        if pred is not None:
            self._pred = pred
        else:
            self._pred = lambda n: n > 0

    def parse(self, text: str) -> typing.Optional[ParseResult]:
        count = 0
        remainder = text
        result = ''
        while remainder:
            res = self._parser.parse(remainder)
            if res is not None:
                count += 1
                remainder = res.remainder
                result += res.text
            else:
                break

        if self._pred(count):
            return self.create_result(text=result, remainder=remainder)
        else:
            return None


class Optional(Parser):
    def __init__(self, parser: Parser):
        assert isinstance(parser, Parser)
        self._parser = parser

    def parse(self, text: str) -> typing.Optional[ParseResult]:
        res = self._parser.parse(text)
        if res is not None:
            return res
        else:
            return self.create_result(text='', remainder=text)


class QuotedString(Parser):
    QUOTATION_MARK = '"'

    def parse(self, text: str) -> typing.Optional[ParseResult]:
        if text[0] != type(self).QUOTATION_MARK:
            return None
        result = type(self).QUOTATION_MARK
        remainder = text[1:]
        while remainder:
            if remainder.startswith('\\' + type(self).QUOTATION_MARK):
                result += type(self).QUOTATION_MARK
                remainder = remainder[2:]
            elif remainder[0] == type(self).QUOTATION_MARK:
                result += type(self).QUOTATION_MARK
                remainder = remainder[1:]
                break
            else:
                result += remainder[0]
                remainder = remainder[1:]
        return self.create_result(text=result, remainder=remainder)

    def __repr__(self):
        return 'QuotedString'


Whitespace = Repeat(Char(str.isspace)).alias('Whitespace')

Literal = Seq(Char(str.isalpha),
              Repeat(Char(str.isalnum))).alias('Literal')

Sign = Char(lambda c: c in ('+', '-'))
Digit = Char(str.isdigit)

FloatingPoint = Seq(Optional(Sign),
                    Repeat(Digit),
                    Char('.'),
                    Repeat(Digit)).alias('FloatingPoint')

Integer = Seq(Optional(Sign),
              Repeat(Digit)).alias('Integer')

Number = Any(FloatingPoint, Integer).alias('Number')

OpeningBracket = Char('[').alias('OpeningBracket')
ClosingBracket = Char(']').alias('ClosingBracket')

Operator = Any(
    String("+"),
    String("-"),
    String("*"),
    String("/"),
    String("^"),
    String("=="),
    String("!="),
    String("<"),
    String("<="),
    String(">"),
    String(">=")).alias('Operator')

text = \
    """
    "Ala ma\n
    kota" 123.9 a12 * 12 [ ala ma kota] 
    """


def tokenize(text: str) -> typing.Iterable[str]:
    parsers = Any(Whitespace, OpeningBracket, ClosingBracket, Number, QuotedString(), Literal, Operator)
    while text:
        # text = text.strip()
        res = parsers.parse(text)
        if res is not None:
            text = res.remainder
            yield res.text, res.parser


# for token in tokenize(text):
#     print(token)

txt = Text(text)
while txt:
    print(txt.read())
