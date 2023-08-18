import string
import typing
from abc import abstractmethod, ABC
from dataclasses import dataclass


@dataclass
class ParseResult:
    text: str
    remainder: str


class Parser(ABC):
    @abstractmethod
    def parse(self, text: str) -> typing.Optional[ParseResult]:
        ...

    def __call__(self, text: str) -> typing.Optional[ParseResult]:
        return self.parse(text)

    def __rshift__(self, other):
        return SequenceParser(self, other)

    def __or__(self, other):
        return AnyParser(self, other)


class CharParser(Parser):
    def __init__(self, pred: typing.Callable[[str], bool]):
        self._pred = pred

    def parse(self, text: str) -> typing.Optional[ParseResult]:
        if text and self._pred(text[0]):
            return ParseResult(text=text[0], remainder=text[1:])
        else:
            return None


class StringParser(Parser):
    def __init__(self, string):
        self._string = string

    def parse(self, text: str) -> typing.Optional[ParseResult]:
        if text and text.startswith(self._string):
            length = len(self._string)
            return ParseResult(text=text[:length], remainder=text[length:])
        else:
            return None


class AnyParser(Parser):
    def __init__(self, *parsers: Parser):
        self._parsers = parsers

    def parse(self, text: str) -> typing.Optional[ParseResult]:
        for parser in self._parsers:
            res = parser(text)
            if res is not None:
                return res
        return None


class SequenceParser(Parser):
    def __init__(self, *parsers: Parser):
        self._parsers = parsers

    def parse(self, text: str) -> typing.Optional[ParseResult]:
        remainder = text
        result = ''
        for parser in self._parsers:
            res = parser(remainder)
            if res is not None:
                remainder = res.remainder
                result += res.text
            else:
                return None
        return ParseResult(text=result, remainder=remainder)


class RepeatedParser(Parser):
    def __init__(self, parser: Parser, pred: typing.Callable[[int], bool] = None):
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
            res = self._parser(remainder)
            if res is not None:
                count += 1
                remainder = res.remainder
                result += res.text
            else:
                break

        if self._pred(count):
            return ParseResult(text=result, remainder=remainder)
        else:
            return None


class OptionalParser(Parser):
    def __init__(self, parser: Parser):
        self._parser = parser

    def parse(self, text: str) -> typing.Optional[ParseResult]:
        res = self._parser(text)
        if res is not None:
            return res
        else:
            return ParseResult(text='', remainder=text)


class QuotedStringParser(Parser):
    def parse(self, text: str) -> typing.Optional[ParseResult]:
        quotation_mark = '"'
        if text[0] != quotation_mark:
            return None
        result = quotation_mark
        txt = text[1:]
        while txt:
            if txt.startswith('\\"'):
                result += quotation_mark
                txt = txt[2:]
            elif txt[0] == quotation_mark:
                result += quotation_mark
                txt = txt[1:]
                break
            else:
                result += txt[0]
                txt = txt[1:]
        return ParseResult(text=result, remainder=txt)


def char(ch):
    if callable(ch):
        return CharParser(ch)
    elif isinstance(ch, str):
        return CharParser(lambda c: c == ch)


any_of = AnyParser
string = StringParser

repeat = RepeatedParser
optional = OptionalParser

whitespace = repeat(char(str.isspace))

literal = char(str.isalpha) \
          >> repeat(char(str.isalnum))

sign = char(lambda c: c in ('+', '-'))
digit = char(str.isdigit)

floating_point = optional(sign) \
                 >> repeat(digit) \
                 >> char('.') \
                 >> repeat(digit)

integer = optional(sign) \
          >> repeat(digit)

number = floating_point | integer
quoted_string = QuotedStringParser()

opening_bracket = char('[')
closing_bracket = char(']')

parser = whitespace

operator = any_of(
    string("+"),
    string("-"),
    string("*"),
    string("/"),
    string("^"),
    string("=="),
    string("!="),
    string("<"),
    string("<="),
    string(">"),
    string(">="))

text = \
    """
    "Ala ma\n
    kota" 123.9 a12 12 [ ala ma kota] 
    """


def tokenize(text: str) -> typing.Iterable[str]:
    parsers = any_of(opening_bracket, closing_bracket, number, quoted_string, literal, operator)
    while text:
        text = text.strip()
        res = parsers(text)
        if res is not None:
            text = res.remainder
            yield res.text.strip()


for token in tokenize(text):
    print(token)
