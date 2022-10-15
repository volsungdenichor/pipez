import pytest

from pipez import opt


def test_map():
    assert 10 >> opt.map(lambda _: 10 * _) == 100
    assert None >> opt.map(lambda _: 10 * _) is None


def test_filter():
    assert 9 >> opt.filter(lambda _: _ < 10) == 9
    assert 11 >> opt.filter(lambda _: _ < 10) is None
    assert None >> opt.filter(lambda _: _ < 10) is None


def test_value_or():
    assert 9 >> opt.value_or(-1) == 9
    assert None >> opt.value_or(-1) == -1


def test_value_or_eval():
    assert 9 >> opt.value_or_eval(lambda: -1) == 9
    assert None >> opt.value_or_eval(lambda: -1) == -1


def test_value_or_raise():
    assert 9 >> opt.value_or_raise(RuntimeError()) == 9
    with pytest.raises(RuntimeError):
        None >> opt.value_or_raise(RuntimeError())
