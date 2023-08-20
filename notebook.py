import itertools
import os
import pathlib
import typing
from datetime import datetime
from operator import itemgetter, attrgetter

import yaml

from pipez import seq, opt


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

    @property
    def is_unique(self):
        return not any(p == Path.ANY for p in self)


class Location:
    def __init__(self, value: typing.Any, path: Path):
        self.value = value
        self.path = path
        assert self.path.is_unique

    def __iter__(self):
        yield self.value
        yield self.path

    def __repr__(self):
        return str(tuple(self))


LocationPredicate = typing.Callable[[Location], bool]


def visit(obj: typing.Any, path=None) -> typing.Iterable[Location]:
    path = path or Path()
    yield Location(obj, path)
    if isinstance(obj, list):
        for index, item in enumerate(obj):
            yield from visit(item, path.child(str(index)))
    elif isinstance(obj, dict):
        for key, value in obj.items():
            yield from visit(value, path.child(key))


class FindResult:
    def __init__(self,
                 note: 'Note',
                 dct: typing.Any,
                 searched_path: Path,
                 locations: typing.Optional[list[Location]] = None):
        self.note = note
        self._dct = dct
        self._searched_path = searched_path
        if locations is not None:
            self._locations = locations
        else:
            self._locations = [loc for loc in visit(self._dct) if loc.path.matches(self._searched_path)]

    def _to_find_result(self, loc: Location) -> 'FindResult':
        return FindResult(self.note, self._dct, loc.path, [loc])

    def __iter__(self) -> typing.Iterable['FindResult']:
        return (self._to_find_result(loc) for loc in self._locations)

    def __repr__(self) -> str:
        return str(self._locations)

    # def __getitem__(self, item) -> 'FindResult':
    #     return self._to_find_result(self._locations[item])

    def __len__(self) -> int:
        return len(self._locations)

    def __bool__(self) -> bool:
        return bool(self._locations)

    def where(self, pred: LocationPredicate) -> 'FindResult':
        return FindResult(self.note,
                          self._dct,
                          self._searched_path,
                          [loc for loc in self if pred(loc)])

    def parent(self) -> 'FindResult':
        return FindResult(self.note, self._dct, self._searched_path.parent())

    def child(self, p) -> 'FindResult':
        return FindResult(self.note, self._dct, self._searched_path.child(p))

    def sibling(self, p) -> 'FindResult':
        return FindResult(self.note, self._dct, self._searched_path.sibling(p))

    def siblings(self) -> 'FindResult':
        return self.parent().child('*').where(lambda loc: loc._searched_path != self._searched_path)

    @property
    def is_unique(self):
        return self._searched_path.is_unique and len(self) == 1

    @property
    def path(self) -> Path:
        assert self.is_unique
        return self._locations[0].path

    @property
    def value(self):
        assert self.is_unique
        return self._locations[0].value

    def link(self) -> 'Note':
        return self.note.vault[self.value]


class Data:
    def __init__(self, note, dct):
        self.note = note
        self._dct = dct

    def __iter__(self) -> typing.Iterable[FindResult]:
        return itertools.chain.from_iterable(
            FindResult(note=self.note, dct=self._dct, searched_path=loc.path, locations=[loc])
            for loc in visit(self._dct))

    def _find_all(self, pred: LocationPredicate) -> typing.Iterable[FindResult]:
        return (find_result for find_result in self if pred(find_result))

    def find(self, predicate: LocationPredicate) -> list[FindResult]:
        return list(self._find_all(predicate))

    def contains(self, predicate: LocationPredicate) -> bool:
        return bool(self.find(predicate))

    def get(self, path) -> FindResult:
        path = Path(path)
        return FindResult(note=self.note, dct=self._dct, searched_path=path)

    def __getitem__(self, path) -> typing.Optional[FindResult]:
        return next(iter(self.get(path)), None)

    def __repr__(self):
        return str(self._dct)


class Note:
    def __init__(self, vault, path: Path, file_location: os.path):
        self.vault = vault
        self.path = path
        self.file_location = file_location

    @property
    def data(self) -> Data:
        if os.path.exists(self.file_location):
            with open(self.file_location, encoding='utf-8') as file:
                # print('  >>> Loading from ', file.name)
                return Data(self, yaml.safe_load(file))
        else:
            return Data(self, {})

    def from_data(self, func):
        return func(self, self.data)

    @property
    def full_name(self) -> str:
        return str(self.path)

    @property
    def name(self) -> str:
        return self.path[-1]

    @property
    def modification_time(self):
        return datetime.datetime.fromtimestamp(pathlib.Path(self.file_location).stat().st_mtime)

    @property
    def creation_time(self):
        return datetime.datetime.fromtimestamp(pathlib.Path(self.file_location).stat().st_ctime)

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

    def _return_note(self, path: Path):
        return Note(vault=self,
                    path=path,
                    file_location=self._path_to_location(path))

    def _location_to_path(self, location: os.path) -> Path:
        return Path(
            os.path.relpath(location, self._directory).replace(os.sep, Path.SEPARATOR)[:-len(Vault.EXTENSION)])

    def _path_to_location(self, path: Path) -> os.path:
        return os.path.join(self._directory, os.sep.join(path)) + Vault.EXTENSION


vault = Vault(r'D:\Users\Krzysiek\Documents\test_notes')


def show(v):
    print(type(v), v)


def get_family(node):
    def get_person(rel_type):
        val = opt.map(attrgetter('value'))

        def result(n: Note, d: Data):
            return node, rel_type, n.name, d['birth'] >> val, d['death'] >> val

        return result

    def pred(loc):
        return loc.value == node and loc.path.matches('children/*')

    for note in vault.notes():
        if note.path.matches('genealogy/*'):
            for loc in note.data.find(pred):
                this = loc.link()
                father, mother = (loc.parent().sibling('parents').child(str(i)) for i in range(2))
                yield father.link().from_data(get_person('father'))
                yield mother.link().from_data(get_person('mother'))
                yield this.from_data(get_person('self'))
                yield from (s.link().from_data(get_person('sibling')) for s in loc.siblings())


for item in get_family('people/Zygmunt August'):
    print(item)

