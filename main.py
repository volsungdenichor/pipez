import copy
import datetime
import itertools
import json
import os
import pathlib
import typing
from json import JSONEncoder
from operator import itemgetter

import yaml

from pipez import seq, tap
from pipez.pipe import fn


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

    def is_unique(self):
        return not any(p == Path.ANY for p in self)


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


LocationPredicate = typing.Callable[[Location], bool]


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

    def where(self, pred: LocationPredicate) -> 'FindResult':
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

    def siblings(self) -> 'FindResult':
        return self.parent().child('*').where(lambda loc: loc.path != self.path)


class Data:
    def __init__(self, dct):
        self._dct = dct

    def __iter__(self) -> typing.Iterable[Location]:
        yield from visit(self._dct)

    def _create_predicate(self,
                          pred: LocationPredicate | typing.Any,
                          path: typing.Optional[Path] = None) -> LocationPredicate:

        if not callable(pred):
            value_pred = lambda loc: loc.value == pred
        else:
            value_pred = pred

        if path is not None:
            path_pred = lambda loc: loc.path.matches(path)
        else:
            path_pred = lambda loc: True

        def predicate(loc: Location) -> bool:
            return value_pred(loc) and path_pred(loc)

        return predicate

    def _find_all(self, pred: LocationPredicate) -> typing.Iterable[FindResult]:
        return (FindResult(self._dct, loc.path) for loc in self if pred(loc))

    def find(self,
             pred: LocationPredicate | typing.Any,
             path: typing.Optional[Path] = None) -> list[Location]:
        predicate = self._create_predicate(pred, path)
        return list(itertools.chain.from_iterable(self._find_all(predicate)))

    def get(self, path) -> FindResult:
        path = Path(path)
        return FindResult(self._dct, path=path)

    def __getitem__(self, path):
        path = Path(path)
        assert path.is_unique()
        return next(iter(FindResult(self._dct, path=path).values), None)

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
    def data(self) -> Data:
        if os.path.exists(self.location):
            with open(self.location, encoding='utf-8') as file:
                return Data(yaml.safe_load(file))
        else:
            return Data({})

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
            data = note.data
            res = visitor(note, data)
            if res is not None:
                yield res

    def backlinks(self, value: Path) -> typing.Iterable[tuple[Note, list[Path]]]:
        value = str(Path(value))
        for note in vault.notes():
            data = note.data
            locs = data.find(value)
            if locs:
                yield note, [loc.path for loc in locs]

    def _return_note(self, path: Path):
        return Note(path=path,
                    location=self._path_to_location(path))

    def _location_to_path(self, location: os.path) -> Path:
        return Path(
            os.path.relpath(location, self._directory).replace(os.sep, Path.SEPARATOR)[:-len(Vault.EXTENSION)])

    def _path_to_location(self, path: Path) -> os.path:
        return os.path.join(self._directory, os.sep.join(path)) + Vault.EXTENSION


def find_parents(vault: Vault, node):
    def visitor(note: Note, data: Data):
        for val, path in data.find(node, 'children/*'):
            return data.get('parents/*').values

    for note in vault.notes():
        if note.path.matches('genealogy/*'):
            data = note.data
            res = visitor(note, data)
            if res is not None:
                yield res


def find_siblings(vault: Vault, node):
    def visitor(note: Note, data: Data):
        for val, path in data.find(node, 'children/*'):
            return data.get('children/*').where(lambda it: it.path != path).values

    for note in vault.notes():
        if note.path.matches('genealogy/*'):
            data = note.data
            res = visitor(note, data)
            if res is not None:
                yield res


def find_spouse_and_children(vault: Vault, node):
    def visitor(note: Note, data: Data):
        for val, path in data.find(node, 'parents/*'):
            spouse = data.get(path).siblings().values[0]
            children = data.get('children/*').values

            for child in children:
                yield spouse, child, vault[child].data['death']

    for note in vault.notes():
        if note.path.matches('genealogy/*'):
            data = note.data
            yield from visitor(note, data)


vault = Vault(r'D:\Users\Krzysiek\Documents\test_notes')

(find_spouse_and_children(vault, 'people/Zygmunt Stary')
 >> seq.for_each(print))

print('---')
(find_parents(vault, 'people/Zygmunt August')
 >> seq.flatten()
 >> seq.to_list()
 >> fn(json.dumps, indent=2)
 >> fn(print))

print('---')
(find_siblings(vault, 'people/Zygmunt August')
 >> seq.flatten()
 >> seq.to_list()
 >> fn(json.dumps, indent=2)
 >> fn(print))

bareja = vault['people/Stanislaw Bareja']
bareja.creation_time >> fn(print)
bareja.modification_time >> fn(print)
bareja.data['death'] >> fn(print)
