import dataclasses
import itertools
import os
import pathlib
import typing
from datetime import datetime
from operator import itemgetter

import yaml
from tabulate import tabulate

from pipez import seq
from pipez.operators import get_item
from pipez.pipe import as_pipeable
from pipez.predicates import any_of


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

        def chunks_match(a, b):
            return a == Path.ANY or b == Path.ANY or a == b

        return len(self._path) == len(other._path) and all(chunks_match(s, o) for s, o in zip(self._path, other._path))

    def __eq__(self, other):
        other = Path(other)
        return self._path == other._path

    @property
    def is_unique(self):
        return not any(p == Path.ANY for p in self)


@dataclasses.dataclass
class Location:
    value: object
    path: Path

    def __repr__(self):
        return f'{self.value}'


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


def to_find_result(dct, loc: Location) -> 'FindResult':
    assert loc.path.is_unique
    return FindResult(dct, loc.path, [loc])


class FindResult:
    def __init__(self,
                 dct: typing.Any,
                 path_or_pattern: Path,
                 locations: typing.Optional[list[Location]] = None):
        self._dct = dct
        self._path_or_pattern = path_or_pattern
        if locations is not None:
            self._locations = locations
        else:
            self._locations = [loc for loc in visit(self._dct) if loc.path.matches(self._path_or_pattern)]

    def _modify_path(self, new_path: Path):
        return FindResult(self._dct, new_path)

    def __iter__(self) -> typing.Iterable['FindResult']:
        return (to_find_result(self._dct, loc) for loc in self._locations)

    def __repr__(self) -> str:
        if not self:
            return str(None)
        else:
            return ', '.join(str(loc) for loc in self._locations)

    def __len__(self) -> int:
        return len(self._locations)

    def __bool__(self) -> bool:
        return bool(self._locations)

    def where(self, pred: LocationPredicate) -> 'FindResult':
        return FindResult(self._dct,
                          self._path_or_pattern,
                          [loc for loc in self if pred(loc)])

    def parent(self) -> 'FindResult':
        return self._modify_path(self._path_or_pattern.parent())

    def child(self, p) -> 'FindResult':
        return self._modify_path(self._path_or_pattern.child(p))

    def sibling(self, p) -> 'FindResult':
        return self._modify_path(self._path_or_pattern.sibling(p))

    def siblings(self) -> 'FindResult':
        return self.parent().child('*').where(lambda loc: loc.path != self._path_or_pattern)

    def as_location(self) -> Location:
        assert self.is_unique
        return self._locations[0]

    @property
    def is_unique(self):
        return self._path_or_pattern.is_unique and len(self) == 1

    @property
    def path(self) -> Path:
        return self.as_location().path

    @property
    def value(self):
        return self.as_location().value


class Data:
    def __init__(self, dct):
        self._dct = dct

    def __iter__(self) -> typing.Iterable[FindResult]:
        return itertools.chain.from_iterable(to_find_result(self._dct, loc) for loc in visit(self._dct))

    def __getitem__(self, path) -> FindResult:
        path = Path(path)
        return FindResult(dct=self._dct, path_or_pattern=path)

    def __repr__(self):
        return str(self._dct)


@dataclasses.dataclass
class Note:
    path: Path
    file_location: os.path

    def __bool__(self):
        return os.path.exists(self.file_location)

    @property
    def data(self) -> Data:
        if self:
            with open(self.file_location, encoding='utf-8') as file:
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
        assert self
        return datetime.datetime.fromtimestamp(pathlib.Path(self.file_location).stat().st_mtime)

    @property
    def creation_time(self):
        assert self
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
        return Note(path=path,
                    file_location=self._path_to_location(path))

    def _location_to_path(self, location: os.path) -> Path:
        return Path(
            os.path.relpath(location, self._directory).replace(os.sep, Path.SEPARATOR)[:-len(Vault.EXTENSION)])

    def _path_to_location(self, path: Path) -> os.path:
        return os.path.join(self._directory, os.sep.join(path)) + Vault.EXTENSION


vault = Vault(r'D:\Users\Krzysiek\Documents\test_notes')


def show(v):
    print(type(v), v)


@as_pipeable
def path_is(loc: Location, path: Path):
    return loc.path.matches(path)


@as_pipeable
def value_is(loc: Location, value):
    return loc.value == value


where = seq.filter
select = seq.map


def get_family(vault: Vault, node):
    def from_data(n: FindResult, rel_type: str):
        assert isinstance(n, FindResult)
        assert n.is_unique
        note = vault[n.value]
        data = note.data
        return {
            'relation': rel_type,
            'note': note.full_name,
            'birth': data['birth/date'],
            'death': data['death/date'],
            'icon': data['icon']
        }

    def create(note: Note, loc: FindResult):
        father, mother = (loc.parent().parent().child(f'parents/{i}') for i in range(2))
        yield loc, 'self'
        yield father, 'father'
        yield mother, 'mother'
        yield from ((s, 'sibling') for s in loc.siblings())

    for note in vault.notes() >> where(path_is('genealogy/*')):
        for loc in note.data >> where(value_is(node) & path_is('children/*')):
            for res, relation in create(note, loc):
                yield from_data(res, relation)


def get_parents(vault: Vault, node):
    def from_data(n: FindResult, rel_type: str):
        assert isinstance(n, FindResult)
        assert n.is_unique
        note = vault[n.value]
        data = note.data
        return {
            'relation': rel_type,
            'note': note.full_name,
            'birth': data['birth/date'],
            'death': data['death/date'],
            'icon': data['icon']
        }

    def get_rels(loc):
        return ({0: 'father', 1: 'mother'}.items()
                >> seq.map(lambda i, rel: (loc.parent().parent().child(f'parents/{i}'), rel)))

    def get(note):
        return (note.data
                >> where(value_is(node) & path_is('children/*'))
                >> seq.flat_map(get_rels)
                >> seq.map(from_data))

    return (vault.notes()
            >> where(path_is('genealogy/*'))
            >> seq.flat_map(get))


def get_grandparents(vault: Vault, node):
    def create(parent, grandparent):
        return {
            'relation': parent['relation'] + '\'s ' + grandparent['relation'],
            'note': grandparent['note'],
            'birth': grandparent['birth'],
            'death': grandparent['death'],
            'icon': grandparent['icon']}

    for parent in get_parents(vault, node):
        yield parent
        yield from get_parents(vault, parent['note']) >> select(lambda gp: create(parent, gp))


print(tabulate(get_family(vault, 'people/Zygmunt Stary')))
print(tabulate(get_grandparents(vault, 'people/Zygmunt Stary')))
