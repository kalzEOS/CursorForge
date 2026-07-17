from __future__ import annotations

from cursorforge.scaler import scale_hotspot


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

    def test_zero_src_size_returns_origin(self) -> None:
        assert scale_hotspot(10, 10, 0, 32) == (0, 0)
