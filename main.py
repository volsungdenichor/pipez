import builtins
import copy
import dataclasses
import datetime
import itertools
import json
import os
import pathlib
import typing
from json import JSONEncoder
from operator import attrgetter

import yaml

from pipez import seq
from pipez.operators import get_attr, get_attr, add, combine, mul, truediv, neg, get_first, get_value, get_item
from pipez.pipe import fn
from pipez.predicates import eq, gt


class Path:
    SEPARATOR = '/'
    ANY = '*'

    def __init__(self, *paths):
        def get(path):
            if isinstance(path, Path):
                return path._path
            elif isinstance(path, str):
                return path.split(type(self).SEPARATOR)
            elif isinstance(path, tuple):
                return (get(p) for p in path)
            elif isinstance(path, int):
                return str(path),
            raise ValueError(path)

        self._path = tuple(itertools.chain.from_iterable(get(p) for p in paths))

    def __repr__(self) -> str:
        return type(self).SEPARATOR.join(map(str, self._path))

    __str__ = __repr__

    def __iter__(self):
        return iter(self._path)

    def __getitem__(self, item):
        return self._path[item]

    def __len__(self):
        return len(self._path)

    def parent(self) -> 'Path':
        return Path(*self._path[:-1])

    def child(self, p) -> 'Path':
        return Path(*(self._path + Path(p)._path))

    def sibling(self, p) -> 'Path':
        return self.parent().child(p)

    def matches(self, other) -> bool:
        other = Path(other)

        def m(a, b):
            return a == Path.ANY or b == Path.ANY or a == b

        return len(self._path) == len(other._path) and all(m(s, o) for s, o in zip(self._path, other._path))

    def __eq__(self, other):
        other = Path(other)
        return self._path == other._path


class Location:
    def __init__(self, value: typing.Any, path: Path):
        self.value = value
        self.path = path

    def __iter__(self):
        yield self.value
        yield self.path

    def __repr__(self) -> str:
        return str(self.value)


def visit(obj: typing.Any) -> typing.Iterable[Location]:
    def impl(o: typing.Any, path: Path) -> typing.Iterable[Location]:
        yield Location(o, path)
        if isinstance(o, list):
            for index, item in enumerate(o):
                yield from impl(item, path.child(str(index)))
        elif isinstance(o, dict):
            for key, value in o.items():
                yield from impl(value, path.child(key))

    yield from impl(obj, Path())


class FindResult:
    def __init__(self,
                 dct: typing.Any,
                 path: Path,
                 result: typing.Optional[list[Location]] = None):
        self._dct = dct
        self.path = path
        if result is not None:
            self._result = result
        else:
            self._result = [loc for loc in visit(self._dct) if loc.path.matches(self.path)]

    def __iter__(self) -> typing.Iterable[Location]:
        return iter(self._result)

    def __repr__(self) -> str:
        return str([item.value for item in self])

    def __getitem__(self, item) -> Location:
        return self._result[item]

    def __len__(self) -> int:
        return len(self._result)

    def __bool__(self) -> bool:
        return bool(self._result)

    def where(self, pred: typing.Callable[[Location], bool]) -> 'FindResult':
        return FindResult(self._dct,
                          self.path,
                          [loc for loc in self if pred(loc)])

    @property
    def paths(self) -> list[Path]:
        return [loc.path for loc in self]

    @property
    def values(self) -> list[typing.Any]:
        return [loc.value for loc in self]

    def parent(self) -> 'FindResult':
        return FindResult(self._dct, self.path.parent())

    def child(self, p) -> 'FindResult':
        return FindResult(self._dct, self.path.child(p))

    def sibling(self, p) -> 'FindResult':
        return FindResult(self._dct, self.path.sibling(p))


class Data:
    def __init__(self, dct):
        self._dct = dct

    def __getitem__(self, item) -> FindResult:
        return FindResult(self._dct, item)

    def __iter__(self) -> typing.Iterable[Location]:
        yield from visit(self._dct)

    def _find_all(self, pred) -> typing.Iterable[FindResult]:
        if not callable(pred):
            value = copy.deepcopy(pred)

            def result(o):
                return o.value == value

            pred = result

        return (FindResult(self._dct, item.path) for item in self if pred(item))

    def find(self, pred) -> list[Location]:
        return list(itertools.chain.from_iterable(self._find_all(pred)))

    def __repr__(self):
        return str(self._dct)


class DataEncoder(JSONEncoder):
    def default(self, obj):
        return obj._dct


class Note:
    def __init__(self, path: Path, location: os.path):
        self.path = path
        self.location = location

    @property
    def data(self) -> list[Data]:
        if os.path.exists(self.location):
            with open(self.location, encoding='utf-8') as file:
                return [Data(d) for d in yaml.safe_load_all(file)]
        else:
            return []

    @property
    def full_name(self) -> str:
        return str(self.path)

    @property
    def name(self) -> str:
        return self.path[-1]

    @property
    def modification_time(self):
        return datetime.datetime.fromtimestamp(pathlib.Path(self.location).stat().st_mtime)

    @property
    def creation_time(self):
        return datetime.datetime.fromtimestamp(pathlib.Path(self.location).stat().st_ctime)

    def __str__(self):
        return self.full_name

    __repr__ = __str__


class Vault:
    EXTENSION = '.md'

    def __init__(self, directory: os.path):
        self._directory = directory

    def notes(self) -> typing.Iterable[Note]:
        for root, dirs, files, in os.walk(self._directory):
            for file in files:
                if file.endswith(Vault.EXTENSION):
                    yield self._return_note(self._location_to_path(os.path.join(root, file)))

    def __getitem__(self, path):
        return self._return_note(Path(path))

    def query(self, visitor):
        for note in self.notes():
            for index, data in enumerate(note.data):
                res = visitor(note, index, data)
                if res is not None:
                    yield res

    def backlinks(self, value: Path) -> typing.Iterable[tuple[Note, int, list[Path]]]:
        value = str(Path(value))
        for note in vault.notes():
            for index, data in enumerate(note.data):
                locs = data.find(value)
                if locs:
                    yield note, index, [loc.path for loc in locs]

    def _return_note(self, path: Path):
        return Note(path=path,
                    location=self._path_to_location(path))

    def _location_to_path(self, location: os.path) -> Path:
        return Path(
            os.path.relpath(location, self._directory).replace(os.sep, Path.SEPARATOR)[:-len(Vault.EXTENSION)])

    def _path_to_location(self, path: Path) -> os.path:
        return os.path.join(self._directory, os.sep.join(path)) + Vault.EXTENSION


def find_parents(node):
    def result(note: Note, index: int, data: Data):
        for val, path in data.find(node):
            if path.matches('children/*'):
                return data['parents/*']

    return result


def find_siblings(node):
    def result(note: Note, index: int, data: Data):
        for val, path in data.find(node):
            if path.matches('children/*'):
                return data['children/*'].where(lambda it: it.path != path)

    return result


def display(o):
    print(f'{o} {type(o)}')


vault = Vault(r'D:\Users\Krzysiek\Documents\test_notes')

node = 'people/Stanisław Bareja'
print(vault[node].full_name)
for n, i, paths in vault.backlinks(node):
    if n.path.matches('movies/*'):
        data = n.data[i]
        print(data['title'], data['year'])
        for p in paths:
            if p.matches('cast/*/actor'):
                print('    aktor', data[p].sibling('character'), 'note:', data[p].sibling('note'), ' {', p, '}')
            if p.matches('director'):
                print('    reżyser')
            if p.matches('story/*') or p.matches('story'):
                print('    scenariusz')
    print('---')

print('---')
for p in vault.query(find_siblings('persons/Jan I Olbracht')) >> seq.first():
    display(p)
