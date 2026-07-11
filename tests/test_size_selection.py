from __future__ import annotations

import pytest


def pick_source_size(available: list[int], target: int) -> int:
    """
    Choose the best source size to scale from.
    - If exact match exists, return it.
    - Otherwise return the closest; ties go to the larger size.
    """
    if not available:
        raise ValueError("no available sizes")
    if target in available:
        return target
    return min(available, key=lambda s: (abs(s - target), -s))


class TestSizeSelection:
    def test_exact_size_returned(self) -> None:
        assert pick_source_size([32, 48, 64], 48) == 48

    def test_nearest_smaller(self) -> None:
        # target 40, available 32 and 64 — 32 is closer
        assert pick_source_size([32, 64], 40) == 32

    def test_nearest_larger(self) -> None:
        # target 56, available 48 and 72 — 48 is closer
        assert pick_source_size([48, 72], 56) == 48

    def test_tie_chooses_larger(self) -> None:
        # target 48, equidistant from 32 and 64
        assert pick_source_size([32, 64], 48) == 64

    def test_single_size_always_returned(self) -> None:
        assert pick_source_size([32], 999) == 32

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError):
            pick_source_size([], 32)
