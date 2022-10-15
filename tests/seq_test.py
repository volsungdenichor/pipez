from operator import itemgetter

from pipez import seq
from pipez.pipe import fn


def fibonacci():
    a, b = 0, 1
    while True:
        a, b = b, a + b
        yield a


def sqr(x):
    return x * x


def is_even(x):
    return x % 2 == 0


def is_odd(x):
    return x % 2 != 0


def test_map():
    assert list(range(5) >> seq.map(sqr)) == [0, 1, 4, 9, 16]


def test_associate():
    assert list(range(10, 15) >> seq.associate(sqr)) == [(10, 100), (11, 121), (12, 144), (13, 169), (14, 196)]


def test_take_if():
    assert list(range(0, 10) >> seq.take_if(is_even)) == [0, 2, 4, 6, 8]


def test_drop_if():
    assert list(range(0, 10) >> seq.drop_if(is_even)) == [1, 3, 5, 7, 9]


def test_replace_if():
    assert list(range(0, 10) >> seq.replace_if(is_even, -1)) == [-1, 1, -1, 3, -1, 5, -1, 7, -1, 9]


def test_replace():
    assert list(range(0, 5) >> seq.replace(2, -1)) == [0, 1, -1, 3, 4]


def test_take():
    assert list(fibonacci() >> seq.take(5)) == [1, 1, 2, 3, 5]


def test_drop():
    assert list(range(10) >> seq.drop(5)) == [5, 6, 7, 8, 9]


def test_step():
    assert list(range(10) >> seq.step(3)) == [0, 3, 6, 9]


def test_exclude():
    assert list(range(10) >> seq.exclude([1, 3, 5, 7])) == [0, 2, 4, 6, 8, 9]


def test_take_while():
    assert list(fibonacci() >> seq.take_while(lambda x: x < 100)) == [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89]
    assert list(fibonacci() >> seq.take_until(lambda x: x >= 100)) == [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89]


def test_drop_while():
    assert list(range(100, 110) >> seq.drop_while(lambda x: x < 105)) == [105, 106, 107, 108, 109]
    assert list(range(100, 110) >> seq.drop_until(lambda x: x >= 105)) == [105, 106, 107, 108, 109]


def test_enumerate():
    assert list(fibonacci() >> seq.take(5) >> seq.enumerate()) == [(0, 1), (1, 1), (2, 2), (3, 3), (4, 5)]
    assert list(fibonacci() >> seq.take(5) >> seq.enumerate(10)) == [(10, 1), (11, 1), (12, 2), (13, 3), (14, 5)]


def test_reverse():
    assert list(range(10) >> seq.reverse()) == [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]


def test_sort():
    assert list([5, 3, 1, 4, 2, 0] >> seq.sort()) == [0, 1, 2, 3, 4, 5]
    assert list([5, 3, 1, 4, 2, 0] >> seq.sort(reverse=True)) == [5, 4, 3, 2, 1, 0]


def test_zip_with():
    assert list(range(5) >> seq.zip_with("alpha")) == [(0, 'a'), (1, 'l'), (2, 'p'), (3, 'h'), (4, 'a')]


def test_flatten():
    assert list(['Alpha', 'Beta'] >> seq.flatten()) == ['A', 'l', 'p', 'h', 'a', 'B', 'e', 't', 'a']


def test_flat_map():
    assert list('alpha' >> seq.flat_map(lambda x: [x, x] if x != 'a' else [])) == ['l', 'l', 'p', 'p', 'h', 'h']


def test_filter_map():
    assert list('alpha' >> seq.filter_map(lambda x: x.upper() if x != 'a' else None)) == ['L', 'P', 'H']


def test_partition():
    t, f = range(10) >> seq.partition(is_even)
    assert list(t) == [0, 2, 4, 6, 8]
    assert list(f) == [1, 3, 5, 7, 9]


def test_all():
    assert [] >> seq.all(lambda x: x >= 100)
    assert range(100, 105) >> seq.all(lambda x: x >= 100)
    assert not range(99, 104) >> seq.all(lambda x: x >= 100)


def test_any():
    assert not [] >> seq.any(lambda x: x >= 100)
    assert range(100, 105) >> seq.any(lambda x: x >= 100)
    assert range(99, 104) >> seq.any(lambda x: x >= 100)


def test_none():
    assert [] >> seq.none(lambda x: x >= 100)
    assert not range(100, 105) >> seq.none(lambda x: x >= 100)
    assert not range(99, 104) >> seq.none(lambda x: x >= 100)


def test_join():
    assert range(5) >> seq.join() == "01234"
    assert range(5) >> seq.join(" ") == "0 1 2 3 4"


def test_to_list():
    assert fibonacci() >> seq.take(5) >> fn(list) == [1, 1, 2, 3, 5]
    assert fibonacci() >> seq.take(5) >> seq.to(list) == [1, 1, 2, 3, 5]
    assert fibonacci() >> seq.take(5) >> seq.to_list() == [1, 1, 2, 3, 5]


def test_to_set():
    assert [1, 2, 2, 3, 3, 4, 5] >> seq.to_set() == {1, 2, 3, 4, 5}


def test_to_tuple():
    assert range(7, 10) >> seq.to_tuple() == (7, 8, 9)


def test_to_dict():
    assert [1, 2, 3, 4] >> seq.to_dict(is_even) == {True: 4, False: 3}


def test_to_multidict():
    assert [1, 2, 3, 4] >> seq.to_multidict(is_even) == {True: [2, 4], False: [1, 3]}


def test_reduce():
    assert [1, 2, 3, 4] >> seq.reduce(lambda total, item: total * item, 1) == 24


def test_sum():
    assert range(101) >> seq.sum() == 5050


def test_min_max():
    rng = [5, 1, 9, 3, 2]
    assert rng >> seq.max() == 9
    assert rng >> seq.min() == 1


def test_first():
    assert fibonacci() >> seq.first() == 1
    assert () >> seq.first() is None


def test_nth():
    assert fibonacci() >> seq.nth(5) == 8
    assert range(3) >> seq.nth(10) is None


def test_extend():
    assert list(fibonacci() >> seq.take(5) >> seq.extend(range(100, 103))) == [1, 1, 2, 3, 5, 100, 101, 102]


def test_chunk():
    assert list(fibonacci() >> seq.chunk(5) >> seq.take(3)) == [
        [1, 1, 2, 3, 5],
        [8, 13, 21, 34, 55],
        [89, 144, 233, 377, 610]
    ]


def test_tail():
    assert list(fibonacci() >> seq.take_while(lambda x: x < 100) >> seq.tail(5)) == [13, 21, 34, 55, 89]


def test_slide():
    assert list(fibonacci() >> seq.slide(3) >> seq.take(3)) == [(1, 1, 2), (1, 2, 3), (2, 3, 5)]
    assert list(range(3) >> seq.slide(3)) == [(0, 1, 2)]
    assert list(range(3) >> seq.slide(5)) == [(0, 1, 2)]
