import pytest

from pipez import opt


def test_map():
    mul_10 = lambda _: 10 * _
    assert 10 >> opt.map(mul_10) == 100
    assert None >> opt.map(mul_10) is None


def test_filter():
    lt_10 = lambda _: _ < 10
    assert 9 >> opt.filter(lt_10) == 9
    assert 11 >> opt.filter(lt_10) is None
    assert None >> opt.filter(lt_10) is None


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


def test_value():
    assert 9 >> opt.value() == 9
    with pytest.raises(RuntimeError):
        None >> opt.value()
