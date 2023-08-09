import json
import operator
import os
from operator import itemgetter

import yaml

from pipez import seq, predicates
from pipez.pipe import as_pipeable, All, fn
from pipez.predicates import eq


def parse_chunk(s: str):
    try:
        return int(s)
    except ValueError:
        return s


class Path:
    def __init__(self, *args):
        if not args:
            self._path = ()
        elif len(args) == 1:
            if isinstance(args[0], tuple):
                self._path = args[0]
            elif isinstance(args[0], str):
                self._path = tuple(parse_chunk(chunk) for chunk in args[0].split('.'))
            elif isinstance(args[0], int):
                self._path = (args[0], 0)
            elif isinstance(args[0], Path):
                self._path = args[0]._path
        else:
            self._path = tuple(args)

    def __repr__(self):
        return '.'.join(map(str, self._path))

    __str__ = __repr__

    def parent(self):
        return Path(self._path[:-1])

    def child(self, key):
        return Path(self._path + (key,))

    def sibling(self, key):
        return self.parent().child(key)

    def matches(self, other):
        other = Path(other)

        def m(aa, bb):
            return aa == '*' or bb == '*' or aa == bb

        return len(self._path) == len(other._path) and all(m(aa, bb) for aa, bb in zip(self._path, other._path))

    def __getitem__(self, item):
        return self._path[item]

    def __eq__(self, other):
        other = Path(other)
        return all(a == b for a, b in zip(self._path, other._path))


@as_pipeable
def visit(obj, path=None):
    path = path or Path()
    yield obj, path
    if isinstance(obj, list):
        for index, item in enumerate(obj):
            yield from item >> visit(path.child(index))
    elif isinstance(obj, dict):
        for key, value in obj.items():
            yield from value >> visit(path.child(key))


get_value = itemgetter(0)
get_path = itemgetter(1)


def value_is(searched_value, op=None):
    op = op or operator.eq
    return lambda v, p: op(v, searched_value)


def path_is(searched_path):
    searched_path = Path(searched_path)
    return lambda v, p: searched_path.matches(p)


class Note:
    def __init__(self, path, root):
        self.path = path
        self.root = root

    def data(self):
        with open(self.path) as file:
            return list(yaml.safe_load_all(file))

    @property
    def name(self):
        return os.path.relpath(self.path, self.root).replace(os.sep, '/')[:-3]

    def __str__(self):
        return self.name

    __repr__ = __str__


class Vault:
    def __init__(self, directory):
        self._directory = directory

    def notes(self):
        for root, dirs, files, in os.walk(self._directory):
            for file in files:
                if file[-3:] == '.md':
                    yield Note(path=os.path.join(root, file), root=self._directory)


@as_pipeable
def find_parents(vault: Vault, node):
    for note in vault.notes():
        for data in note.data():
            if data >> visit() >> predicates.contains(All(value_is(node), path_is('children.*'))):
                return (data
                        >> visit()
                        >> seq.filter(path_is('parents.*'))
                        >> seq.map(get_value)
                        >> seq.to_list())
    return []


@as_pipeable
def find_siblings(vault: Vault, node):
    for note in vault.notes():
        for data in note.data():
            if data >> visit() >> predicates.contains(All(value_is(node), path_is('children.*'))):
                return (data
                        >> visit()
                        >> seq.filter(All(path_is('children.*'), value_is(node, operator.ne)))
                        >> seq.map(get_value)
                        >> seq.to_list())
    return []


@as_pipeable
def find_grandparents(vault: Vault, node):
    return (vault
            >> find_parents(node)
            >> seq.flat_map(lambda p: vault >> find_parents(p))
            >> seq.to_list())


pipe = (find_siblings('persons/Jan I Olbracht')
        >> fn(json.dumps, indent=2)
        >> fn(print))

print(pipe)

vault = Vault(r'D:\Users\Krzysiek\Documents\test_notes')
(vault >> pipe)
print('--')
