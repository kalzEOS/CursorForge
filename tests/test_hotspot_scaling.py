from __future__ import annotations

import pytest


def scale_hotspot(
    xhot: int, yhot: int, source_size: int, target_size: int
) -> tuple[int, int]:
    """Scale a hotspot from source_size to target_size, clamped to [0, target_size-1]."""
    scale = target_size / source_size
    new_x = round(xhot * scale)
    new_y = round(yhot * scale)
    new_x = max(0, min(target_size - 1, new_x))
    new_y = max(0, min(target_size - 1, new_y))
    return new_x, new_y


class TestHotspotScaling:
    def test_zero_hotspot_stays_zero(self) -> None:
        assert scale_hotspot(0, 0, 32, 64) == (0, 0)

    def test_normal_hotspot_scales(self) -> None:
        x, y = scale_hotspot(16, 16, 32, 64)
        assert x == 32
        assert y == 32

    def test_enlargement(self) -> None:
        x, y = scale_hotspot(8, 8, 32, 64)
        assert x == 16
        assert y == 16

    def test_reduction(self) -> None:
        x, y = scale_hotspot(32, 32, 64, 32)
        assert x == 16
        assert y == 16

    def test_clamp_upper_bound(self) -> None:
        # hotspot at edge of source, scaled up — must not exceed target-1
        x, y = scale_hotspot(31, 31, 32, 32)
        assert x <= 31
        assert y <= 31

    def test_clamp_prevents_negative(self) -> None:
        x, y = scale_hotspot(0, 0, 32, 16)
        assert x >= 0
        assert y >= 0

    def test_equal_source_and_target_unchanged(self) -> None:
        assert scale_hotspot(10, 20, 48, 48) == (10, 20)

    def test_rounding(self) -> None:
        # 1 * (48/32) = 1.5 -> rounds to 2
        x, _ = scale_hotspot(1, 0, 32, 48)
        assert x == 2
