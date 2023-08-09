from pipez.predicates import ge, is_none, is_empty, lt, ne, contains, each, eq, size_is, has_prefix, has_suffix, \
    contains_subrange


def test_all():
    # pred = Any(All(ge(0), lt(5), ne(3)), eq(9))
    pred = (ge(0) & lt(5) & ne(3)) | eq(9)
    assert not -1 >> pred
    assert 0 >> pred
    assert 1 >> pred
    assert 2 >> pred
    assert not 3 >> pred
    assert 4 >> pred
    assert not 5 >> pred
    assert not 6 >> pred
    assert not 7 >> pred
    assert not 8 >> pred
    assert 9 >> pred


def test_is_none():
    assert None >> is_none
    assert 3 >> ~is_none


def test_is_empty():
    assert [] >> is_empty
    assert not [1, 2, 3] >> is_empty


def test_each():
    ge_100 = ge(100)
    assert [] >> each(ge_100)
    assert range(100, 105) >> each(ge_100)
    assert not range(99, 104) >> each(ge_100)


def test_contains():
    ge_100 = ge(100)
    assert not [] >> contains(ge_100)
    assert range(100, 105) >> contains(ge_100)
    assert range(99, 104) >> contains(ge_100)


def test_does_not_contain():
    ge_100 = ge(100)
    assert [] >> ~contains(ge_100)
    assert not range(100, 105) >> ~contains(ge_100)
    assert not range(99, 104) >> ~contains(ge_100)


def test_size_is():
    has_len_ge_3 = size_is(ge(3))
    assert not [1, 2] >> has_len_ge_3
    assert [1, 2, 3] >> has_len_ge_3
    assert [1, 2, 3, 4] >> has_len_ge_3


def test_has_prefix():
    starts_with_abc = has_prefix('abc')
    assert 'abc' >> starts_with_abc
    assert 'abcde' >> starts_with_abc
    assert not 'ab' >> starts_with_abc


def test_has_suffix():
    ends_with_abc = has_suffix('123')
    assert '123' >> ends_with_abc
    assert '0123' >> ends_with_abc
    assert not '12345' >> ends_with_abc


def test_contains_subrange():
    contains_123 = contains_subrange('123')
    assert '123' >> contains_123
    assert '1234' >> contains_123
    assert '0123' >> contains_123
    assert '01234' >> contains_123
    assert not '12' >> contains_123
    assert not '' >> contains_123
