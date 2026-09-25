"""Regression: the API's resultSizeEstimate is capped, and a short fetch must
not look like a complete one."""

import pytest

from mailagent.client import IncompleteFetch


def test_incomplete_fetch_carries_partial_and_missing():
    exc = IncompleteFetch("2 of 5 missing", missing=["a", "b"], partial=[1, 2, 3])
    assert exc.missing == ["a", "b"]
    assert exc.partial == [1, 2, 3]
    with pytest.raises(IncompleteFetch):
        raise exc
