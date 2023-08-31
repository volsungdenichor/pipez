import dataclasses
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

    def at(self, index: int):
        return self._text[self._index + index]

    def peek(self) -> Token:
        return Token(text=self.at(0), pos=self.pos)

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
